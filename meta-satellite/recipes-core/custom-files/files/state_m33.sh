#!/bin/sh

RPROC_PATH="/sys/class/remoteproc/remoteproc0"

echo "[INFO] Checking M33 state..."
if [ -f $RPROC_PATH/state ]; then
    cat $RPROC_PATH/state
else
    echo "[ERROR] remoteproc0 not found!"
fi
