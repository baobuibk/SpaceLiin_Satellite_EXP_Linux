#!/bin/sh

# ----------- Configurable Paths ------------
ZIP_FILE=~/tmp/libcsp.zip
SRC_BASE=~/.a55_src
DEST_DIR=$SRC_BASE/00_src
TOOLS_DIR=~/tools

DATA_BASE=/data
A55_DATA_DIR=$DATA_BASE/.a55_src
SCRIPT_DIR=$A55_DATA_DIR/scripts
TMP_PART_DIR=$A55_DATA_DIR/tmp_part
DAILY_DIR=$DATA_BASE/Daily
ONESHOT_DIR=$DATA_BASE/Oneshot
AUTOTEST_DIR=$DATA_BASE/Autotest

DATE_FOLDER=$(date +%y%d%m)
EPOCH_TIME=$(date +%s)

# ----------- Step 1: Prepare directories ------------
echo "[1/8] Creating directory structure..."
mkdir -p "$DEST_DIR" "$A55_DATA_DIR/01_data" "$SCRIPT_DIR" "$TMP_PART_DIR" \
         "$DAILY_DIR/HighRes" "$DAILY_DIR/LowRes" "$ONESHOT_DIR" \
         "$AUTOTEST_DIR" "$A55_DATA_DIR/Autotest_img_low" "$A55_DATA_DIR/Autotest_img_high" "$A55_DATA_DIR/Autotest_data"

# ----------- Step 2: Unzip source ------------
echo "[2/8] Unzipping $ZIP_FILE to $DEST_DIR..."
unzip -o "$ZIP_FILE" -d "$DEST_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to unzip archive."
    exit 1
fi

# ----------- Step 3: Ensure waf is executable ------------
WAF_PATH=$(find "$DEST_DIR" -type f -name waf 2>/dev/null | head -n 1)
if [ -n "$WAF_PATH" ]; then
    chmod +x "$WAF_PATH"
    echo "[3/8] Set executable permission for waf → $WAF_PATH"
else
    echo "Warning: No waf file found after unzip."
fi

# ----------- Step 4: Run allbuild.sh ------------
BUILD_SCRIPT="$DEST_DIR/libcsp/allbuild.sh"
if [ -f "$BUILD_SCRIPT" ]; then
    echo "[4/8] Running allbuild.sh..."
    chmod +x "$BUILD_SCRIPT"
    cd "$(dirname "$BUILD_SCRIPT")" || {
        echo "Error: Cannot change directory to script."
        exit 1
    }
    ./allbuild.sh
else
    echo "Error: $BUILD_SCRIPT not found."
    exit 1
fi

# ----------- Step 5: Copy example files from DevSrc ------------
EXAMPLE_SRC="$DEST_DIR/libcsp/00_Dev16/DevSrc"
echo "[5/8] Copying example files from $EXAMPLE_SRC..."

if [ -f "$EXAMPLE_SRC/H000000_CAM0_0000000000.zip" ]; then
    cp "$EXAMPLE_SRC/H000000_CAM0_0000000000.zip" "$DAILY_DIR/HighRes/"
    echo "→ Copied H000000_CAM0_0000000000.zip → $DAILY_DIR/HighRes/"
else
    echo "Warning: H000000_CAM0_0000000000.zip not found."
fi

if [ -f "$EXAMPLE_SRC/L000000_CAM0_0000000000.zip" ]; then
    cp "$EXAMPLE_SRC/L000000_CAM0_0000000000.zip" "$DAILY_DIR/LowRes/"
    echo "→ Copied L000000_CAM0_0000000000.zip → $DAILY_DIR/LowRes/"
else
    echo "Warning: L000000_CAM0_0000000000.zip not found."
fi

if [ -f "$EXAMPLE_SRC/python_exec.py" ]; then
    cp "$EXAMPLE_SRC/python_exec.py" "$SCRIPT_DIR/"
    echo "→ Copied python_exec.py → $SCRIPT_DIR/"
else
    echo "Warning: python_exec.py not found."
fi

SRC_ELF="/home/root/tools/payexp_m33.elf"
DST_ELF="/home/bee/payexp_m33.elf"

echo "[6.5] Copying payexp_m33.elf..."
if [ -f "$SRC_ELF" ]; then
    cp "$SRC_ELF" "$DST_ELF"
    echo "→ Copied $SRC_ELF → $DST_ELF"
else
    echo "Warning: $SRC_ELF not found."
fi

# ----------- Step 6: Verify results ------------
echo "[6/8] Verifying copied files..."
ls -l "$DAILY_DIR/HighRes" "$DAILY_DIR/LowRes" "$SCRIPT_DIR" | grep -E 'zip|py' || echo "No example files found."

# ----------- Step 7: Check Autotest structure ------------
echo "[7/8] Checking Autotest folders..."
for dir in "$AUTOTEST_DIR" "$A55_DATA_DIR/Autotest_img_low" "$A55_DATA_DIR/Autotest_img_high" "$A55_DATA_DIR/Autotest_data"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "→ Created missing directory: $dir"
    else
        echo "✓ Exists: $dir"
    fi
done

# ----------- Step 8: Summary ------------
echo "[8/8] Final structure under /data:"
tree "$DATA_BASE" -L 3

echo "[v] All done successfully!"
