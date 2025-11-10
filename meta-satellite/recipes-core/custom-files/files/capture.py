#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime

def run_cmd(cmd, timeout=5):
    """Chạy lệnh shell với timeout"""
    try:
        print(f"[CMD] {cmd}")
        subprocess.run(cmd, shell=True, check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Command timeout after {timeout}s: {cmd}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")

def capture_ar2020(cam_id, mode):
    """Chụp ảnh từ camera AR2020 (0–3)"""
    # === SWITCH SENSOR/PCA bằng sysfs ===
    print(f"[INFO] Switching to AR2020 camera {cam_id}...")
    lane_path = "/sys/bus/i2c/devices/2-0070/lane_switch/current_lane"
    sensor_path = "/sys/bus/i2c/devices/2-0020/sensor_switch/current_sensor"

    try:
        run_cmd(f"echo {cam_id} > {lane_path}", timeout=2)
        run_cmd(f"echo {cam_id} > {sensor_path}", timeout=2)
    except Exception as e:
        print(f"[WARN] Switch sensor/pca failed: {e}")

    time.sleep(1.5)  # đợi ổn định 1s

    # === CHỤP ẢNH ===
    epoch = int(time.time())
    save_dir = "/data/.a55_src/tmp"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{mode}_CAM{cam_id}_{epoch}.raw"
    filepath = os.path.join(save_dir, filename)

    cmd = (
        f'v4l2-ctl --device=/dev/video0 '
        f'--set-fmt-video=width=5120,height=3840,pixelformat=BA10 && '
        f'v4l2-ctl --device=/dev/video0 '
        f'--stream-mmap --stream-count=1 --stream-to="{filepath}" --verbose'
    )
    run_cmd(cmd, timeout=5)
    print(f"[DONE] Captured: {filepath}")

def capture_usb_cam(cam_id):
    """Chụp ảnh từ camera USB (cam_id = 4)"""
    print("[INFO] Enabling USB camera power (gpio 24)...")
    run_cmd("gpioset -t0 -c gpiochip1 24=1", timeout=5)
    time.sleep(3)  # đợi ổn định

    epoch = int(time.time())
    filename = f"oneshot_UCA0_{epoch}.jpg"
    filepath = os.path.join("/data/.a55_src/tmp", filename)
    os.makedirs("/data/.a55_src/tmp", exist_ok=True)

    cmd = (
        f'v4l2-ctl --device=/dev/video1 '
        f'--set-fmt-video=width=1280,height=720,pixelformat=MJPG && '
        f'v4l2-ctl --device=/dev/video1 '
        f'--stream-mmap --stream-count=1 --stream-to="{filepath}"'
    )
    run_cmd(cmd, timeout=5)
    print(f"[DONE] Captured: {filepath}")

    print("[INFO] Disabling USB camera power...")
    run_cmd("gpioset -t0 -c gpiochip1 24=0", timeout=5)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 capture.py <camera_id> [--daily|--oneshot]")
        sys.exit(1)

    cam_id = int(sys.argv[1])
    mode = "--oneshot"
    if len(sys.argv) > 2:
        mode = sys.argv[2]

    # ========= Alias mapping cho test =========
    if cam_id == 10:
        print("[INFO] Alias: cam 10 → AR2020 cam0 (side test)")
        capture_ar2020(0, "oneshot")  
        return
    elif cam_id == 12:
        print("[INFO] Alias: cam 12 → AR2020 cam2 (side test)")
        capture_ar2020(2, "oneshot")  
        return
    # ==========================================

    if cam_id in range(0, 4):
        if mode == "--daily":
            capture_ar2020(cam_id, "daily")
        else:
            capture_ar2020(cam_id, "oneshot")
    elif cam_id == 4:
        capture_usb_cam(cam_id)
    else:
        print(f"[ERROR] Unsupported camera id: {cam_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()
