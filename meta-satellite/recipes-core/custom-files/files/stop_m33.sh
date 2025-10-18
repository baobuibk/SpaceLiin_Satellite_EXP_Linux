#!/bin/sh

RPROC_PATH="/sys/class/remoteproc/remoteproc0"

echo "[INFO] Stopping M33 core..."
if [ -f $RPROC_PATH/state ]; then
    echo stop > $RPROC_PATH/state
    echo "[INFO] Current state:"
    cat $RPROC_PATH/state
else
    echo "[ERROR] remoteproc0 not found!"
fi
