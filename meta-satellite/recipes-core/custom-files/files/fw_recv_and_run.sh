#!/bin/sh

FW_PATH="/home/root"
DEFAULT_FW_NAME="payexp_m33.elf"

if [ -n "$1" ]; then
    FW_NAME="$1"
else
    FW_NAME="$DEFAULT_FW_NAME"
fi

FULL_FW="$FW_PATH/$FW_NAME"

echo "[INFO] Cleaning old firmware..."
rm -f "$FULL_FW"

echo "[INFO] Stopping M33 core..."
bash /home/root/tools/stop_m33.sh

echo "[INFO] Waiting for firmware via rz..."
cd "$FW_PATH"
rz -y

sleep 0.2

if [ -s "$FULL_FW" ]; then
    echo "[INFO] Firmware received: $FULL_FW"
    bash /home/root/tools/run_m33.sh "$FULL_FW"
else
    echo "[ERROR] Firmware not received or file is empty!"
    exit 1
fi
