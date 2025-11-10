#!/usr/bin/env python3
import sys
import os
import struct
import mmap
import time
import fcntl
import select
from pathlib import Path
import threading
import subprocess
import queue
import socket
from collections import deque
import sqlite3
import re

UNIX_SOCKET_PATH = "/tmp/rpmsg_cmd.sock"
DB_PATH = "/data/.a55_src/bee_params.db"

# Device paths
TTY_DEVICE = "/dev/ttyRPMSG30"
DMA_DEVICE = "/dev/rpmsg_dma30"
OUTPUT_DIR = "/data/.a55_src/tmp"

# IOCTL definitions
RPMSG_IOC_MAGIC = ord('R')
RPMSG_GET_DMA_INFO = (2 << 30) | (16 << 16) | (RPMSG_IOC_MAGIC << 8) | 1

def _now_ms():
    return int(time.time() * 1000)

class RPMSGTester:
    """
    Single-reader-thread architecture:
      - Exactly one RX thread owns tty_fd reads and dispatches lines.
      - send_command() only writes and (optionally) waits for an "OK" via a waiter queue.
      - Prevents race conditions where a listener eats responses intended for send_command().
    """
    def __init__(self):
        # FDs / DMA mapping
        self.tty_fd = None
        self.dma_fd = None
        self.dma_map = None
        self.dma_size = 0
        self.dma_phys = 0
        self.pending_ok = deque()

        # Concurrency primitives
        self.tty_lock = threading.Lock()          # serialize writes to TTY
        self.rx_thread = None
        self.rx_stop = threading.Event()

        # Queues / structures
        self.cmd_queue = queue.Queue(maxsize=50)  # producer (events) -> sender worker
        self.ok_waiters = deque()                 # FIFO of queues waiting for "OK" response
        self.ok_lock = threading.Lock()

        self.queue_worker_thread = None

        # UNIX sockets to interact with external C processes
        self.bee_tx_path = "/tmp/bee_to_rpmsg.sock"   # Python BIND to receive EVENT from C
        self.bee_rx_path = "/tmp/rpmsg_to_bee.sock"   # Python SEND CMD to C

        # RX buffering (accumulate partial frames)
        self._rx_buf = bytearray()

    # ------------- Device Management -------------
    def open_devices(self):
        print("Opening RPMSG devices...")
        # Open TTY for commands
        try:
            self.tty_fd = os.open(TTY_DEVICE, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            print(f"[v] Command channel opened: {TTY_DEVICE}")
            # Set raw mode
            import tty
            tty.setraw(self.tty_fd)
            print(f"[v] Command channel opened: {TTY_DEVICE} (RAW mode)")
        except Exception as e:
            print(f"[x] Failed to open TTY: {e}")
            return False

        # Open DMA device
        try:
            self.dma_fd = os.open(DMA_DEVICE, os.O_RDWR | os.O_NONBLOCK)
            print(f"[v] DMA channel opened: {DMA_DEVICE}")
        except Exception as e:
            print(f"[x] Failed to open DMA device: {e}")
            os.close(self.tty_fd)
            self.tty_fd = None
            return False

        # Get DMA info
        try:
            import array
            buf = array.array('Q', [0, 0])  # Two uint64_t
            fcntl.ioctl(self.dma_fd, RPMSG_GET_DMA_INFO, buf, True)
            self.dma_phys = buf[0]
            self.dma_size = buf[1]
            print(f"\nDMA Buffer Info:")
            print(f"  Physical Address: 0x{self.dma_phys:x}")
            print(f"  Size: {self.dma_size / (1024*1024):.0f} MB ({self.dma_size} bytes)")
        except Exception as e:
            print(f"[x] Failed to get DMA info: {e}")
            return False

        # mmap DMA buffer (read-only from Python side)
        try:
            self.dma_map = mmap.mmap(self.dma_fd, self.dma_size, mmap.MAP_SHARED, mmap.PROT_READ)
            print(f"[v] DMA buffer mapped to Python")
        except Exception as e:
            print(f"[x] Failed to mmap: {e}")
            return False

        print()
        return True

    def close_devices(self):
        self.rx_stop.set()
        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=1.0)
        if self.dma_map:
            self.dma_map.close()
            self.dma_map = None
        if self.dma_fd:
            try:
                os.close(self.dma_fd)
            except Exception:
                pass
            self.dma_fd = None
        if self.tty_fd:
            try:
                os.close(self.tty_fd)
            except Exception:
                pass
            self.tty_fd = None
        print("Devices closed")

    # ------------- TX (Commands) -------------
    def send_command(self, cmd, cmd_prefix='#', timeout=2.0, wait_ok=True):
        """
        Write a command to tty and optionally wait for a line containing 'OK'.
        No direct reads here -> RX thread will capture responses and resolve waiters.
        """
        full = f"{cmd_prefix}{cmd}\r"
        print(f"\n>>> Sending command: {full.strip()}")
        try:
            # register a waiter BEFORE sending to avoid race
            waiter = None
            if wait_ok:
                waiter = queue.Queue(maxsize=1)
                with self.ok_lock:
                    self.ok_waiters.append(waiter)
                    # Nếu có OK đến trước, trả ngay
                    if self.pending_ok:
                        early = self.pending_ok.popleft()
                        try:
                            waiter.put_nowait(early)
                            print(f"[DBG] Delivered early OK: {early}")
                            return early
                        except queue.Full:
                            pass

            # write
            with self.tty_lock:
                os.write(self.tty_fd, full.encode('utf-8'))

            if not wait_ok:
                return None

            # wait for OK (resolved by RX thread)
            try:
                line = waiter.get(timeout=timeout)
                print(f"<<< Matched response: {line.strip()}")
                return line
            except queue.Empty:
                print("[x] Timeout waiting for response (OK)")
                return None
        except Exception as e:
            print(f"[x] Command failed: {e}")
            # if we failed to send, clean up the waiter slot
            if wait_ok:
                with self.ok_lock:
                    try:
                        self.ok_waiters.remove(waiter)
                    except ValueError:
                        pass
            return None

    def _update_param_db(self, updates: dict):
        """Cập nhật giá trị tham số trong SQLite DB."""
        if not updates:
            return
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                for addr, val in updates.items():
                    c.execute(
                        "REPLACE INTO bee_param_update (addr, value) VALUES (?, ?);",
                        (addr, val)
                    )
                conn.commit()
            print(f"[DB] Updated {len(updates)} parameters → {DB_PATH}")
        except Exception as e:
            print(f"[DB-ERROR] {e}")

    def _handle_capture(self, args):
        """
        Xử lý command capture <num>
        Ví dụ:
          capture 0  → chạy python3 /home/root/tools/capture.py 0 --daily
          capture 4  → chạy python3 /home/root/tools/capture.py 4 --oneshot
        """
        try:
            if not args:
                # self._send_response("-capture error: missing camera index")
                return

            cam_idx = args[0]
            if not cam_idx.isdigit():
                # self._send_response(f"-capture error: invalid index {cam_idx}")
                return

            cam_idx = int(cam_idx)
            mode_flag = "--daily" if cam_idx != 4 else "--oneshot"

            cmd = ["python3", "/home/root/tools/capture.py", str(cam_idx), mode_flag]
            print(f"[v] Executing capture: {' '.join(cmd)}")

            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=60).decode("utf-8", errors="ignore")
            print(f"[v] capture.py output:\n{output}")
            # self._send_response(f"-capture done {cam_idx}")
        except subprocess.CalledProcessError as e:
            err_msg = e.output.decode("utf-8", errors="ignore")
            print(f"[x] capture.py failed: {err_msg}")
            # self._send_response(f"-capture failed {e.returncode}")
        except subprocess.TimeoutExpired:
            print("[x] capture.py timeout")
            # self._send_response("-capture timeout")
        except Exception as e:
            print(f"[x] capture exception: {e}")
            # self._send_response(f"-capture error {str(e)}")

    # ------------- RX (Reader) -------------
    def start_receiver(self):
        if self.rx_thread and self.rx_thread.is_alive():
            return
        self.rx_stop.clear()
        self.rx_thread = threading.Thread(target=self._rx_loop, name="rpmsg-rx", daemon=True)
        self.rx_thread.start()
        print("[v] RX thread started (sole reader of tty_fd)")

    def _rx_loop(self):
        print("[v] RX loop running (exclusive reader)")
        fd = self.tty_fd
        while not self.rx_stop.is_set():
            try:
                r, _, _ = select.select([fd], [], [], 0.5)
                if not r:
                    continue
                chunk = os.read(fd, 4096)
                if not chunk:
                    # no data
                    continue
                self._rx_buf.extend(chunk)

                # Split into lines by either \n or \r
                while True:
                    # find earliest newline (\n or \r)
                    nl_idx = None
                    for sep in (b'\n', b'\r'):
                        i = self._rx_buf.find(sep)
                        if i != -1:
                            nl_idx = i if nl_idx is None else min(nl_idx, i)
                    if nl_idx is None:
                        break  # incomplete line

                    line = self._rx_buf[:nl_idx]
                    # drop all immediate newline chars at front (handle \r\n combos)
                    drop = nl_idx + 1
                    while drop < len(self._rx_buf) and self._rx_buf[drop:drop+1] in (b'\n', b'\r'):
                        drop += 1
                    self._rx_buf = self._rx_buf[drop:]

                    text = line.decode('utf-8', errors='ignore').strip()
                    if not text:
                        continue
                    self._dispatch_line(text)

            except Exception as e:
                print(f"[x] RX error: {e}")
                time.sleep(0.2)

    def _handle_update_param(self, text: str):
        """
        Nhận chuỗi như:
          '0x602=1,0x603=55,0x604=77'
        → Cập nhật DB theo các giá trị đó.
        """
        try:
            updates = {}
            # tách theo dấu phẩy
            for pair in text.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                m = re.match(r"(0x[0-9A-Fa-f]+)\s*=\s*(-?\d+)", pair)
                if not m:
                    print(f"[WARN] Bỏ qua: {pair}")
                    continue
                addr = int(m.group(1), 16)
                val = int(m.group(2))
                updates[addr] = val

            if updates:
                self._update_param_db(updates)
                # self._send_response(f"-update_param OK {len(updates)}")

        except Exception as e:
            print(f"[x] update_param error: {e}")
            # self._send_response(f"-update_param error {str(e)}")


    def _dispatch_line(self, text: str):
        # Debug raw RX
        print(f"[RX] {text}")
        print(f"[DBG] repr(text) = {repr(text)}  (len={len(text)})")
        # Fast-path: OK resolution
        clean = text.replace('\x00', '').replace('\r', '').replace('\n', '').strip().upper()
        if clean == "OK":
            with self.ok_lock:
                if self.ok_waiters:
                    q = self.ok_waiters.popleft()
                    q.put_nowait(clean)
                    print("[DBG] OK delivered to waiter")
                else:
                    self.pending_ok.append(clean)
                    print("[DBG] Stored early OK (no waiter yet)")
            return

        # Incoming commands from M33 (e.g., "a55_ping")
        parts = text.split()
        if parts:
            name = parts[0]
            if name == "a55_ping":
                print("[v] Handling 'a55_ping' -> reply '-a55_pong'")
                self._send_response("-a55_pong")
                return
            elif name == "a55_exec":
                self._handle_exec(parts[1:])
                return
            elif name == "update_param":
                self._handle_update_param(" ".join(parts[1:]))
                return
            elif name == "capture":
                self._handle_capture(parts[1:] if len(parts) > 1 else [])
                return
        # Otherwise, just log
        # (You may route other message types here if firmware defines them)
        # print(f"[RX-INFO] {text}")

    def _handle_exec(self, args):
        if not args:
            self._send_response("-Error: missing script name")
            return
        script_name = args[0]
        script_path = f"/home/root/tools/{script_name}"
        if not os.path.exists(script_path):
            self._send_response(f"-Error: script not found {script_name}")
            return
        print(f"[v] Executing script: {script_path}")
        try:
            output = subprocess.check_output(
                ["/bin/sh", script_path],
                stderr=subprocess.STDOUT,
                timeout=30
            ).decode('utf-8', errors='ignore')
            print(f"[v] Script output:\n{output}")
            self._send_response(f"-exec done: {script_name}")
        except subprocess.CalledProcessError as e:
            self._send_response(f"-exec failed: {e.returncode}")
            try:
                print(f"[x] Script error: {e.output.decode('utf-8', errors='ignore')}")
            except Exception:
                pass
        except Exception as e:
            self._send_response(f"-exec exception: {str(e)}")

    def _send_response(self, resp: str):
        try:
            msg = (resp + "\n").encode('utf-8')
            with self.tty_lock:
                os.write(self.tty_fd, msg)
            print(f">>> Sent response to M33: {resp}")
        except Exception as e:
            print(f"[x] Failed to send response: {e}")

    # ------------- DMA/File Transfer -------------
    def wait_for_file_notification(self, timeout=10.0):
        print(f"\nWaiting for file notification (timeout: {timeout}s)...")
        try:
            # Wait with select
            r, _, _ = select.select([self.dma_fd], [], [], timeout)
            if not r:
                print("[x] Timeout - no file notification received")
                return None

            # struct { uint8_t type, flags; uint16_t reserved;
            #          uint32_t offset, size; char filename[240]; }
            msg_data = os.read(self.dma_fd, 256)
            if len(msg_data) < 256:
                print(f"[x] Incomplete message: {len(msg_data)} bytes")
                return None

            # Parse header: target(1) + type(1) + flags(1) + reserved(2) + offset(4) + size(4)
            target, msg_type, flags, reserved, offset, size = struct.unpack('<BBBBHII', msg_data[:13])
            filename = msg_data[13:256].split(b'\x00')[0].decode('utf-8')

            print(f"\n[v] File notification received:")
            print(f"  Target: 0x{target:02x}")
            print(f"  Type: 0x{msg_type:02x}")
            print(f"  Filename: {filename}")
            print(f"  Offset: 0x{offset:x} ({offset / (1024*1024):.2f} MB)")
            print(f"  Size: {size} bytes ({size / (1024*1024):.2f} MB)")

            return {'type': msg_type, 'filename': filename, 'offset': offset, 'size': size}
        except Exception as e:
            print(f"[x] Error waiting for file: {e}")
            return None

    def read_file_from_dma(self, file_info):
        filename = file_info['filename']
        offset = file_info['offset']
        size = file_info['size']
        print(f"\nReading file from DMA buffer...")
        if offset + size > self.dma_size:
            print(f"[x] Invalid offset/size exceeds DMA buffer!")
            return False
        try:
            self.dma_map.seek(offset)
            data = self.dma_map.read(size)
            output_path = os.path.join(OUTPUT_DIR, filename)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)
            print(f"[v] File saved: {output_path}")
            print(f"  Size: {len(data)} bytes")
            if filename.endswith(('.txt', '.log')):
                preview = data[:200].decode('utf-8', errors='ignore')
                print(f"  Preview: {preview[:100]}...")
            return True
        except Exception as e:
            print(f"[x] Failed to read/save file: {e}")
            return False

    # ------------- Background Workers -------------
    def start_queue_worker(self):
        if self.queue_worker_thread and self.queue_worker_thread.is_alive():
            return
        self.queue_worker_thread = threading.Thread(target=self._queue_worker_loop, daemon=True)
        self.queue_worker_thread.start()
        print("[v] Command queue worker started")

    def _queue_worker_loop(self):
        print("[v] Queue worker running")
        while True:
            try:
                item = self.cmd_queue.get()  # (cmd_text, tries_allowed)
                if item is None:
                    break
                cmd_text, tries_allowed = item
                success = False
                for attempt in range(1, tries_allowed + 1):
                    print(f"[Q] Sending '{cmd_text}' attempt {attempt}/{tries_allowed}")
                    resp = self.send_command(cmd_text, cmd_prefix='#', timeout=2.0, wait_ok=True)
                    if resp and "OK" in resp:
                        print(f"[Q] Command '{cmd_text}' succeeded (OK found).")
                        success = True
                        break
                    else:
                        print(f"[Q] Command '{cmd_text}' no OK, retrying...")
                        time.sleep(0.2)
                if not success:
                    print(f"[Q] Command '{cmd_text}' failed after {tries_allowed} attempts (timeout).")
                self.cmd_queue.task_done()
            except Exception as e:
                print(f"[x] Queue worker error: {e}")
                time.sleep(0.5)

    # ------------- Modes -------------
    def interactive_mode(self):
        print("\n" + "="*50)
        print("Interactive Mode")
        print("Commands: #cmd (req), $cmd (file), -cmd (resp), =cmd (file resp)")
        print("Type 'quit' to exit")
        print("="*50)
        while True:
            try:
                cmd = input("\nCommand> ").strip()
                if cmd.lower() in ['quit', 'exit', 'q']:
                    break
                if not cmd:
                    continue
                prefix = '#'
                if cmd[0] in ('#', '$', '-', '='):
                    prefix = cmd[0]
                    cmd = cmd[1:].strip()
                wait_ok = (prefix == '#')  # heuristic: normal req expects OK
                self.send_command(cmd, cmd_prefix=prefix, timeout=5.0, wait_ok=wait_ok)
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"Error: {e}")





# ----------------------- UNIX helpers -----------------------
def unix_event_listener(tester: RPMSGTester):
    """Listen for EVENT messages from bee_unix_pub_event (C)"""
    path = tester.bee_tx_path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(path)
    print(f"[UNIX-EVT] Listening on {path} (from C) ...")
    while True:
        try:
            data, _ = sock.recvfrom(256)
            text = data.decode().strip()
            if not text:
                continue
            print(f"[UNIX-EVT] {text}")
            parts = text.split()
            if len(parts) >= 3 and parts[0].upper() == "EVENT":
                # Bỏ chữ EVENT, chỉ giữ name và val
                name = parts[1]
                val = parts[2]
                cmd_to_send = f"{name} {val}"
                try:
                    tester.cmd_queue.put_nowait((cmd_to_send, 2))
                    print(f"[UNIX-EVT] Enqueued {cmd_to_send}")
                except queue.Full:
                    print(f"[UNIX-EVT] Queue full, drop {cmd_to_send}")
        except Exception as e:
            print(f"[x] UNIX-EVT error: {e}")
            time.sleep(0.5)

def unix_cmd_sender(tester: RPMSGTester):
    """Send CMD messages from RPMSG → C Table"""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    dest = tester.bee_rx_path
    print(f"[UNIX-CMD] Ready to send CMD to {dest}")
    while True:
        cmd = input("CMD> ").strip()
        if not cmd:
            continue
        msg = f"CMD {cmd}"
        sock.sendto(msg.encode(), (dest))
        print(f"[UNIX-CMD] Sent: {msg}")

def test_file_transfer(tester: RPMSGTester):
    print("\n" + "="*50)
    print("Testing File Transfer")
    print("="*50)
    print("\nWaiting for M33 to send a file...")
    print("(Run M33 firmware with send_file() call)")
    file_info = tester.wait_for_file_notification(timeout=30.0)
    if file_info:
        tester.read_file_from_dma(file_info)
    else:
        print("\nNo file received. Make sure M33 firmware is running and sending files.")

def monitor_mode(tester: RPMSGTester):
    print("\n" + "="*50)
    print("Monitor Mode - Waiting for files from M33")
    print("Press Ctrl+C to stop")
    print("="*50)
    try:
        while True:
            file_info = tester.wait_for_file_notification(timeout=5.0)
            if file_info:
                tester.read_file_from_dma(file_info)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")

def interactive_mode(tester: RPMSGTester):
    tester.interactive_mode()

def unix_listener(tester: RPMSGTester):
    """Listen for local commands via Unix socket and forward to RPMSG"""
    try:
        os.unlink(UNIX_SOCKET_PATH)
    except FileNotFoundError:
        pass
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(UNIX_SOCKET_PATH)
    print(f"[UNIX] Listening for commands on {UNIX_SOCKET_PATH} ...")
    while True:
        try:
            data, _ = server.recvfrom(256)
            text = data.decode().strip()
            if not text:
                continue
            print(f"[UNIX] Received command: {text}")
            tester.send_command(text, cmd_prefix="#", timeout=5.0, wait_ok=True)
        except Exception as e:
            print(f"[x] UNIX listener error: {e}")
            time.sleep(1)

# ----------------------- main -----------------------
def main():
    print("="*60)
    print("RPMSG Test Tool - Python Edition (single-reader-thread)")
    print("="*60)

    mode = "menu"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    tester = RPMSGTester()

    if not tester.open_devices():
        print("\nFailed to open devices. Check:")
        print("  1. Kernel module loaded: lsmod | grep rpmsg")
        print("  2. Devices exist: ls -l /dev/ttyRPMSG* /dev/rpmsg_dma*")
        print("  3. M33 firmware is running")
        return 1
    else:
        tester.start_receiver()
        threading.Thread(target=unix_listener, args=(tester,), daemon=True).start()
        tester.start_queue_worker()
        threading.Thread(target=unix_event_listener, args=(tester,), daemon=True).start()

    try:
        if mode == "files":
            test_file_transfer(tester)
        elif mode == "monitor":
            monitor_mode(tester)
        elif mode == "interactive":
            interactive_mode(tester)
        else:
            # Menu loop
            while True:
                print("\n" + "="*50)
                print("Select test mode:")
                print("  1. Test file transfer (wait for M33)")
                print("  2. Monitor mode (continuous)")
                print("  3. Interactive command mode")
                print("  4. Quit")
                print("="*50)
                choice = input("\nChoice> ").strip()
                if choice == "1":
                    test_file_transfer(tester)
                elif choice == "2":
                    monitor_mode(tester)
                elif choice == "3":
                    interactive_mode(tester)
                elif choice == "4":
                    break
                else:
                    print("Invalid choice")
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        tester.close_devices()

    print("\nTest complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
