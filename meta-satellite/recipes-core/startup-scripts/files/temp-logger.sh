#!/bin/sh
# temp-logger.sh

LOCK_FILE="/tmp/temp-logger.lock"
LOG_FILE="/home/root/temp.log"

if [ -e "$LOCK_FILE" ]; then
    echo "Already! Exit!"
    exit 1
fi

touch "$LOCK_FILE"

cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

for i in $(seq 1 10); do
    DATE=$(date +"%Y-%m-%d %H:%M:%S")
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    echo "$DATE  $((TEMP / 1000)).$((TEMP % 1000)) C" >> "$LOG_FILE"
    sleep 5
done
