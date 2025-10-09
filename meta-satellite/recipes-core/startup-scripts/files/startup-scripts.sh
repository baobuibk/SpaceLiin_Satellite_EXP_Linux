#!/bin/sh
# startup.sh - runs at boot and executes all scripts found in /home/root/scripts.d/
# Design: you can drop additional scripts into /home/root/scripts.d/ and they will be started.
# Example: an additional script "temp-logger.sh" can loop and write to /home/root/temp.log

SCRIPTS_DIR="/home/root/scripts.d"
LOGFILE="/home/root/custom-scripts.log"

echo "$(date '+%F %T') [Startup] Starting" >> $LOGFILE

# Make sure directory exists
mkdir -p "$SCRIPTS_DIR"

# Start each executable script in background (so multiple can run)
for f in "$SCRIPTS_DIR"/*.sh; do
    [ -f "$f" ] || continue
    if [ -x "$f" ]; then
        echo "$(date '+%F %T') [Startup] Launching $f" >> $LOGFILE
        # start in background; redirect stdout/stderr
        "$f" >> ${f}.log 2>&1 &
    else
        echo "$(date '+%F %T') [Startup] $f is not executable, skipping" >> $LOGFILE
    fi
done

# Keep the main script alive so systemd tracks it (or you can exit and let systemd manage child restarts)
# In this design, we simply sleep forever because children run in background and service uses Restart=always
while true; do
    sleep 3600
done
