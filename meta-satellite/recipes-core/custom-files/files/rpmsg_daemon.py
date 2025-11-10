#!/usr/bin/env python3
"""
RPMSG Daemon - Communication service with M33
Runs as background daemon, other processes communicate via Unix sockets
"""
import sys
import os
import time
import select
import threading
import subprocess
import queue
import socket
from collections import deque
import sqlite3
import re

# Unix socket paths
UNIX_CMD_SOCKET = "/tmp/rpmsg_cmd.sock"      # Receive commands from other processes
UNIX_EVENT_SOCKET = "/tmp/bee_to_rpmsg.sock" # Receive events from C processes
UNIX_RESP_SOCKET = "/tmp/rpmsg_resp.sock"    # Send responses back

# Device path
TTY_DEVICE = "/dev/ttyRPMSG30"

# Database
DB_PATH = "/data/.a55_src/bee_params.db"

def _now_ms():
    return int(time.time() * 1000)

class RPMSGDaemon:
    """
    RPMSG Communication Daemon
    - Single RX thread for reading from M33
    - Unix socket server for receiving commands from other processes
    - Queue-based command sender with retry logic
    """
    def __init__(self):
        # TTY device
        self.tty_fd = None
        
        # Concurrency
        self.tty_lock = threading.Lock()
        self.rx_thread = None
        self.rx_stop = threading.Event()
        
        # Command queue and OK waiters
        self.cmd_queue = queue.Queue(maxsize=100)
        self.ok_waiters = deque()
        self.ok_lock = threading.Lock()
        self.pending_ok = deque()
        
        # Workers
        self.queue_worker_thread = None
        self.unix_server_thread = None
        self.unix_event_thread = None
        
        # RX buffer
        self._rx_buf = bytearray()
        
        # Response routing (for clients waiting for responses)
        self.response_callbacks = {}
        self.response_lock = threading.Lock()

    def open_device(self):
        """Open TTY device for RPMSG communication - retry until success"""
        print(f"[DAEMON] Opening {TTY_DEVICE}...")
        retry_count = 0
        while True:
            try:
                self.tty_fd = os.open(TTY_DEVICE, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                import tty
                tty.setraw(self.tty_fd)
                print(f"[DAEMON] TTY opened in RAW mode")
                return True
            except Exception as e:
                retry_count += 1
                if retry_count == 1 or retry_count % 10 == 0:
                    print(f"[WARN] Failed to open TTY (attempt {retry_count}): {e}")
                    print(f"[WARN] Waiting for {TTY_DEVICE} to become available...")
                time.sleep(2)  # Wait 2 seconds before retry

    def close_device(self):
        """Close TTY device"""
        self.rx_stop.set()
        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=2.0)
        if self.tty_fd:
            try:
                os.close(self.tty_fd)
            except Exception:
                pass
            self.tty_fd = None
        print("[DAEMON] Device closed")

    # ------------- TX (Commands) -------------
    def send_command(self, cmd, cmd_prefix='#', timeout=2.0, wait_ok=True):
        """Send command to M33 and optionally wait for OK"""
        full = f"{cmd_prefix}{cmd}\r"
        print(f"[TX] Sending: {full.strip()}")
        
        try:
            waiter = None
            if wait_ok:
                waiter = queue.Queue(maxsize=1)
                with self.ok_lock:
                    self.ok_waiters.append(waiter)
                    if self.pending_ok:
                        early = self.pending_ok.popleft()
                        try:
                            waiter.put_nowait(early)
                            return early
                        except queue.Full:
                            pass
            
            # Write to TTY
            with self.tty_lock:
                os.write(self.tty_fd, full.encode('utf-8'))
            
            if not wait_ok:
                return None
            
            # Wait for OK
            try:
                line = waiter.get(timeout=timeout)
                print(f"[TX] Got response: {line.strip()}")
                return line
            except queue.Empty:
                print(f"[TX] Timeout waiting for OK")
                return None
                
        except Exception as e:
            print(f"[ERROR] Command failed: {e}")
            if wait_ok and waiter:
                with self.ok_lock:
                    try:
                        self.ok_waiters.remove(waiter)
                    except ValueError:
                        pass
            return None

    def _send_response(self, resp: str):
        """Send response back to M33"""
        try:
            msg = (resp + "\n").encode('utf-8')
            with self.tty_lock:
                os.write(self.tty_fd, msg)
            print(f"[TX] Response to M33: {resp}")
        except Exception as e:
            print(f"[ERROR] Failed to send response: {e}")

    # ------------- RX (Reader) -------------
    def start_receiver(self):
        """Start RX thread to read from M33"""
        if self.rx_thread and self.rx_thread.is_alive():
            return
        self.rx_stop.clear()
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()
        print("[DAEMON] RX thread started")

    def _rx_loop(self):
        """Main RX loop - sole reader of TTY"""
        fd = self.tty_fd
        while not self.rx_stop.is_set():
            try:
                r, _, _ = select.select([fd], [], [], 0.5)
                if not r:
                    continue
                    
                chunk = os.read(fd, 4096)
                if not chunk:
                    continue
                    
                self._rx_buf.extend(chunk)
                
                # Split into lines
                while True:
                    nl_idx = None
                    for sep in (b'\n', b'\r'):
                        i = self._rx_buf.find(sep)
                        if i != -1:
                            nl_idx = i if nl_idx is None else min(nl_idx, i)
                    if nl_idx is None:
                        break
                    
                    line = self._rx_buf[:nl_idx]
                    drop = nl_idx + 1
                    while drop < len(self._rx_buf) and self._rx_buf[drop:drop+1] in (b'\n', b'\r'):
                        drop += 1
                    self._rx_buf = self._rx_buf[drop:]
                    
                    text = line.decode('utf-8', errors='ignore').strip()
                    if text:
                        self._dispatch_line(text)
                        
            except Exception as e:
                print(f"[ERROR] RX error: {e}")
                time.sleep(0.2)

    def _dispatch_line(self, text: str):
        """Dispatch received line from M33"""
        print(f"[RX] {text}")
        
        # Handle OK responses
        clean = text.replace('\x00', '').replace('\r', '').replace('\n', '').strip().upper()
        if clean == "OK":
            with self.ok_lock:
                if self.ok_waiters:
                    q = self.ok_waiters.popleft()
                    q.put_nowait(clean)
                else:
                    self.pending_ok.append(clean)
            return
        
        # Handle commands from M33
        parts = text.split()
        if not parts:
            return
            
        cmd = parts[0]
        args = parts[1:]
        
        if cmd == "a55_ping":
            self._send_response("-a55_pong")
        elif cmd == "a55_exec":
            self._handle_exec(args)
        elif cmd == "update_param":
            self._handle_update_param(" ".join(args))
        elif cmd == "capture":
            self._handle_capture(args)
        else:
            print(f"[RX] Unknown command: {cmd}")

    # ------------- Command Handlers -------------
    def _handle_exec(self, args):
        """Execute shell script"""
        if not args:
            self._send_response("-Error: missing script name")
            return
            
        script_name = args[0]
        script_path = f"/home/root/tools/{script_name}"
        
        if not os.path.exists(script_path):
            self._send_response(f"-Error: script not found {script_name}")
            return
            
        print(f"[EXEC] Running: {script_path}")
        try:
            output = subprocess.check_output(
                ["/bin/sh", script_path],
                stderr=subprocess.STDOUT,
                timeout=30
            ).decode('utf-8', errors='ignore')
            print(f"[EXEC] Output:\n{output}")
            self._send_response(f"-exec done: {script_name}")
        except subprocess.CalledProcessError as e:
            self._send_response(f"-exec failed: {e.returncode}")
        except Exception as e:
            self._send_response(f"-exec exception: {str(e)}")

    def _handle_update_param(self, text: str):
        """Update parameters in database"""
        try:
            updates = {}
            for pair in text.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                m = re.match(r"(0x[0-9A-Fa-f]+)\s*=\s*(-?\d+)", pair)
                if not m:
                    print(f"[WARN] Invalid param: {pair}")
                    continue
                addr = int(m.group(1), 16)
                val = int(m.group(2))
                updates[addr] = val
            
            if updates:
                self._update_param_db(updates)
                
        except Exception as e:
            print(f"[ERROR] update_param: {e}")

    def _update_param_db(self, updates: dict):
        """Update parameters in SQLite database"""
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
            print(f"[DB] Updated {len(updates)} parameters")
        except Exception as e:
            print(f"[ERROR] DB update: {e}")

    def _handle_capture(self, args):
        """Handle capture command"""
        try:
            if not args or not args[0].isdigit():
                return
            
            cam_idx = int(args[0])
            mode_flag = "--daily" if cam_idx != 4 else "--oneshot"
            
            cmd = ["python3", "/home/root/tools/capture.py", str(cam_idx), mode_flag]
            print(f"[CAPTURE] Running: {' '.join(cmd)}")
            
            output = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=60
            ).decode("utf-8", errors="ignore")
            print(f"[CAPTURE] Output:\n{output}")
            
        except Exception as e:
            print(f"[ERROR] Capture failed: {e}")

    # ------------- Queue Worker -------------
    def start_queue_worker(self):
        """Start command queue worker"""
        if self.queue_worker_thread and self.queue_worker_thread.is_alive():
            return
        self.queue_worker_thread = threading.Thread(target=self._queue_worker_loop, daemon=True)
        self.queue_worker_thread.start()
        print("[DAEMON] Queue worker started")

    def _queue_worker_loop(self):
        """Process commands from queue with retry logic"""
        while True:
            try:
                item = self.cmd_queue.get()
                if item is None:
                    break
                    
                cmd_text, tries_allowed = item
                success = False
                
                for attempt in range(1, tries_allowed + 1):
                    print(f"[QUEUE] Sending '{cmd_text}' (attempt {attempt}/{tries_allowed})")
                    resp = self.send_command(cmd_text, cmd_prefix='#', timeout=2.0, wait_ok=True)
                    
                    if resp and "OK" in resp:
                        print(f"[QUEUE] Command succeeded")
                        success = True
                        break
                    else:
                        time.sleep(0.2)
                
                if not success:
                    print(f"[QUEUE] Command failed after {tries_allowed} attempts")
                    
                self.cmd_queue.task_done()
                
            except Exception as e:
                print(f"[ERROR] Queue worker: {e}")
                time.sleep(0.5)

    # ------------- Unix Socket Servers -------------
    def start_unix_server(self):
        """Start Unix socket server for receiving commands"""
        if self.unix_server_thread and self.unix_server_thread.is_alive():
            return
        self.unix_server_thread = threading.Thread(target=self._unix_server_loop, daemon=True)
        self.unix_server_thread.start()
        print("[DAEMON] Unix server started")

    def _unix_server_loop(self):
        """Listen for commands from other processes"""
        try:
            os.unlink(UNIX_CMD_SOCKET)
        except FileNotFoundError:
            pass
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(UNIX_CMD_SOCKET)
        os.chmod(UNIX_CMD_SOCKET, 0o666)  # Allow all processes to send
        
        print(f"[UNIX] Listening on {UNIX_CMD_SOCKET}")
        
        while True:
            try:
                data, addr = sock.recvfrom(512)
                text = data.decode().strip()
                if not text:
                    continue
                
                print(f"[UNIX] Received: {text}")
                
                # Send command immediately (no queue for Unix commands)
                self.send_command(text, cmd_prefix='#', timeout=5.0, wait_ok=True)
                
            except Exception as e:
                print(f"[ERROR] Unix server: {e}")
                time.sleep(0.5)

    def start_unix_event_listener(self):
        """Start Unix socket listener for events from C processes"""
        if self.unix_event_thread and self.unix_event_thread.is_alive():
            return
        self.unix_event_thread = threading.Thread(target=self._unix_event_loop, daemon=True)
        self.unix_event_thread.start()
        print("[DAEMON] Unix event listener started")

    def _unix_event_loop(self):
        """Listen for EVENT messages from C processes"""
        try:
            os.unlink(UNIX_EVENT_SOCKET)
        except FileNotFoundError:
            pass
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(UNIX_EVENT_SOCKET)
        os.chmod(UNIX_EVENT_SOCKET, 0o666)
        
        print(f"[UNIX] Event listener on {UNIX_EVENT_SOCKET}")
        
        while True:
            try:
                data, _ = sock.recvfrom(256)
                text = data.decode().strip()
                if not text:
                    continue
                
                print(f"[EVENT] {text}")
                
                # Parse "EVENT name value" format
                parts = text.split()
                if len(parts) >= 3 and parts[0].upper() == "EVENT":
                    name = parts[1]
                    val = parts[2]
                    cmd = f"{name} {val}"
                    
                    # Queue with retry
                    try:
                        self.cmd_queue.put_nowait((cmd, 2))
                        print(f"[EVENT] Queued: {cmd}")
                    except queue.Full:
                        print(f"[EVENT] Queue full, dropped: {cmd}")
                        
            except Exception as e:
                print(f"[ERROR] Event listener: {e}")
                time.sleep(0.5)

    # ------------- Main Daemon Loop -------------
    def run(self):
        """Run daemon - blocking call"""
        print("\n" + "="*60)
        print("RPMSG Daemon Starting...")
        print("="*60)
        
        # This will retry until device opens successfully
        self.open_device()
        
        # Start all workers
        self.start_receiver()
        self.start_queue_worker()
        self.start_unix_server()
        self.start_unix_event_listener()
        
        print("\n[DAEMON] All services started, daemon is running...")
        print("[DAEMON] Press Ctrl+C to stop\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[DAEMON] Shutting down...")
        finally:
            self.close_device()
        
        return 0

# ------------- Main Entry Point -------------
def main():
    daemon = RPMSGDaemon()
    return daemon.run()

if __name__ == "__main__":
    sys.exit(main())
