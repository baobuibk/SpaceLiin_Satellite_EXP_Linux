#!/usr/bin/env python3
"""
File Transfer Daemon - DMA file transfer service
Runs as background daemon, continuously monitors for files from M33
"""
import sys
import os
import struct
import mmap
import time
import fcntl
import select
from pathlib import Path

# Device path
DMA_DEVICE = "/dev/rpmsg_dma30"
OUTPUT_DIR = "/data/.a55_src/tmp"

# IOCTL definitions
RPMSG_IOC_MAGIC = ord('R')
RPMSG_GET_DMA_INFO = (2 << 30) | (16 << 16) | (RPMSG_IOC_MAGIC << 8) | 1

class FileTransferDaemon:
    """
    File Transfer Daemon
    - Monitors DMA device for incoming file notifications
    - Reads files from DMA buffer and saves to disk
    """
    def __init__(self):
        self.dma_fd = None
        self.dma_map = None
        self.dma_size = 0
        self.dma_phys = 0
        
        # Stats
        self.files_received = 0
        self.total_bytes = 0

    def open_dma_device(self):
        """Open and initialize DMA device - retry until success"""
        print(f"[DMA] Opening {DMA_DEVICE}...")
        retry_count = 0
        
        # Step 1: Open device
        while True:
            try:
                self.dma_fd = os.open(DMA_DEVICE, os.O_RDWR)
                print(f"[DMA] Device opened")
                break
            except Exception as e:
                retry_count += 1
                if retry_count == 1 or retry_count % 10 == 0:
                    print(f"[WARN] Failed to open DMA device (attempt {retry_count}): {e}")
                    print(f"[WARN] Waiting for {DMA_DEVICE} to become available...")
                time.sleep(2)
        
        # Step 2: Get DMA buffer info
        retry_count = 0
        while True:
            try:
                import array
                buf = array.array('Q', [0, 0])  # Two uint64_t
                fcntl.ioctl(self.dma_fd, RPMSG_GET_DMA_INFO, buf, True)
                self.dma_phys = buf[0]
                self.dma_size = buf[1]
                
                print(f"\n[DMA] Buffer Info:")
                print(f"  Physical Address: 0x{self.dma_phys:x}")
                print(f"  Size: {self.dma_size / (1024*1024):.0f} MB ({self.dma_size} bytes)")
                break
            except Exception as e:
                retry_count += 1
                if retry_count == 1 or retry_count % 10 == 0:
                    print(f"[WARN] Failed to get DMA info (attempt {retry_count}): {e}")
                time.sleep(2)
        
        # Step 3: mmap DMA buffer
        retry_count = 0
        while True:
            try:
                self.dma_map = mmap.mmap(
                    self.dma_fd,
                    self.dma_size,
                    mmap.MAP_SHARED,
                    mmap.PROT_READ
                )
                print(f"[DMA] Buffer mapped successfully\n")
                return True
            except Exception as e:
                retry_count += 1
                if retry_count == 1 or retry_count % 10 == 0:
                    print(f"[WARN] Failed to mmap (attempt {retry_count}): {e}")
                time.sleep(2)

    def close_dma_device(self):
        """Close DMA device and cleanup"""
        if self.dma_map:
            self.dma_map.close()
            self.dma_map = None
        
        if self.dma_fd:
            try:
                os.close(self.dma_fd)
            except Exception:
                pass
            self.dma_fd = None
        
        print("[DMA] Device closed")

    def wait_for_file_notification(self, timeout=10.0):
        """
        Wait for file notification from M33
        Returns file info dict or None on timeout/error
        """
        try:
            # Set non-blocking mode
            flags = fcntl.fcntl(self.dma_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.dma_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            # Wait with select
            ready = select.select([self.dma_fd], [], [], timeout)
            
            if not ready[0]:
                return None
            
            # Read notification message - C struct sends 253 bytes (13 + 240)
            # Not 256! The driver/firmware sends exactly what's needed
            msg_data = os.read(self.dma_fd, 1024)  # Read more than needed
            actual_size = len(msg_data)
            
            # Debug: show what we got
            if actual_size > 0:
                print(f"[DEBUG] Received {actual_size} bytes")
            
            # Need at least 13 bytes for header
            if actual_size < 13:
                print(f"[WARN] Message too short: {actual_size} bytes (need at least 13)")
                return None
            
            # Parse header using PACKED format (no padding)
            # C struct: target(1) + type(1) + flags(1) + reserved(2) + offset(4) + size(4) = 13 bytes
            # Format: B=uint8, H=uint16, I=uint32
            # Use '=' for native byte order with standard sizes (no alignment padding)
            target, msg_type, flags, reserved, offset, size = struct.unpack(
                '=BBBHII', msg_data[:13]
            )
            
            # Filename starts at byte 13, C sends 240 bytes for filename
            filename_bytes = msg_data[13:] if actual_size > 13 else b''
            filename = filename_bytes.split(b'\x00')[0].decode('utf-8', errors='ignore')
            
            print(f"\n[FILE] Notification received:")
            print(f"  Target: 0x{target:02x}")
            print(f"  Type: 0x{msg_type:02x}")
            print(f"  Flags: 0x{flags:02x}")
            print(f"  Reserved: 0x{reserved:04x}")
            print(f"  Filename: {filename}")
            print(f"  Offset: 0x{offset:x} ({offset / (1024*1024):.2f} MB)")
            print(f"  Size: {size} bytes ({size / (1024*1024):.2f} MB)")
            
            return {
                'type': msg_type,
                'filename': filename,
                'offset': offset,
                'size': size,
                'timestamp': int(time.time())
            }
            
        except BlockingIOError:
            # No data available, normal for non-blocking mode
            return None
        except Exception as e:
            import traceback
            print(f"[ERROR] Wait for file: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return None

    def read_file_from_dma(self, file_info):
        """Read file data from DMA buffer and save to disk"""
        filename = file_info['filename']
        offset = file_info['offset']
        size = file_info['size']
        
        print(f"[FILE] Reading from DMA buffer...")
        
        # Validate offset and size
        if offset + size > self.dma_size:
            print(f"[ERROR] Invalid offset/size exceeds DMA buffer!")
            return False
        
        try:
            # Read from DMA buffer
            self.dma_map.seek(offset)
            data = self.dma_map.read(size)
            
            # Save to disk
            output_path = os.path.join(OUTPUT_DIR, filename)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(data)
            
            print(f"[FILE] Saved: {output_path}")
            print(f"  Size: {len(data)} bytes")
            
            # Update stats
            self.files_received += 1
            self.total_bytes += len(data)
            
            # Preview for text files
            if filename.endswith(('.txt', '.log', '.json', '.xml')):
                try:
                    preview = data[:200].decode('utf-8', errors='ignore')
                    print(f"  Preview: {preview[:100]}...")
                except Exception:
                    pass
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to read/save file: {e}")
            return False

    def print_stats(self):
        """Print daemon statistics"""
        if self.files_received > 0:
            print(f"\n[STATS] Files received: {self.files_received}")
            print(f"[STATS] Total bytes: {self.total_bytes} ({self.total_bytes / (1024*1024):.2f} MB)")

    def monitor_loop(self):
        """Main monitoring loop"""
        print("="*60)
        print("File Transfer Daemon - Monitoring for files...")
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        last_stats = time.time()
        
        try:
            while True:
                # Wait for file notification (5 second timeout for periodic tasks)
                file_info = self.wait_for_file_notification(timeout=5.0)
                
                if file_info:
                    # File received, read and save it
                    self.read_file_from_dma(file_info)
                
                # Print stats every 60 seconds if there's activity
                now = time.time()
                if self.files_received > 0 and (now - last_stats) >= 60:
                    self.print_stats()
                    last_stats = now
                
                # Small sleep to avoid busy loop
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n[DAEMON] Stopping...")
        finally:
            self.print_stats()

    def run(self):
        """Run daemon - main entry point"""
        print("\n" + "="*60)
        print("File Transfer Daemon Starting...")
        print("="*60 + "\n")
        
        # This will retry until device opens successfully
        self.open_dma_device()
        
        try:
            self.monitor_loop()
        finally:
            self.close_dma_device()
        
        print("\n[DAEMON] Stopped")
        return 0

# ------------- Main Entry Point -------------
def main():
    daemon = FileTransferDaemon()
    return daemon.run()

if __name__ == "__main__":
    sys.exit(main())
