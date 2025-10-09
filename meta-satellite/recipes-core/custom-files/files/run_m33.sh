#!/bin/sh

REMOTE_PROC="/sys/class/remoteproc/remoteproc0"

if [ $# -ne 1 ]; then
    echo "Usage: $0 /absolute/path/to/file.elf"
    exit 1
fi

ELF_PATH="$1"

if [ ! -f "$ELF_PATH" ]; then
    echo "Error: ELF file not found: $ELF_PATH"
    exit 1
fi

ELF_FILE="$(basename "$ELF_PATH")"

echo "Copying $ELF_PATH to /lib/firmware/$ELF_FILE ..."
cp "$ELF_PATH" /lib/firmware/

if [ $? -ne 0 ]; then
    echo "Error: Failed to copy ELF file"
    exit 1
fi

echo "$ELF_FILE" > "$REMOTE_PROC/firmware"

echo "Starting remoteproc with $ELF_FILE ..."
echo start > "$REMOTE_PROC/state"

echo "Done. M33 should now be running $ELF_FILE"
