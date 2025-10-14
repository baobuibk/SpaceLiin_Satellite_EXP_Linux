#!/bin/sh

# ----------- Configurable Paths ------------
ZIP_FILE=~/tmp/libcsp.zip
DEST_DIR=~/.a55_src/00_src
TOOLS_DIR=~/tools
DATA_BASE=~/.a55_src/01_data
DATE_FOLDER=$(date +%y%d%m)
EPOCH_TIME=$(date +%s)

# ----------- Step 1: Unzip ------------
mkdir -p "$DEST_DIR"
echo "Unzipping $ZIP_FILE into $DEST_DIR..."
unzip -o "$ZIP_FILE" -d "$DEST_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to unzip archive."
    exit 1
fi

# ----------- Step 2: Run allbuild.sh ------------
BUILD_SCRIPT="$DEST_DIR/libcsp/allbuild.sh"
if [ -f "$BUILD_SCRIPT" ]; then
    echo "Setting executable permission for $BUILD_SCRIPT"
    chmod +x "$BUILD_SCRIPT"
else
    echo "Error: $BUILD_SCRIPT not found."
    exit 1
fi

cd "$(dirname "$BUILD_SCRIPT")" || {
    echo "Error: Cannot change directory to script."
    exit 1
}
echo "Running allbuild.sh..."
./allbuild.sh

# ----------- Step 3: Create folder tree ------------
HIGHRES_DIR="$DATA_BASE/$DATE_FOLDER/HighResolution"
LOWRES_DIR="$DATA_BASE/$DATE_FOLDER/LowResolution"
mkdir -p "$HIGHRES_DIR" "$LOWRES_DIR"

# Helper function: generate next file ID (0000–9999)
get_next_id() {
    local dir="$1"
    local count
    count=$(find "$dir" -maxdepth 1 -type f | wc -l)
    printf "%04d" "$count"
}

# ----------- Step 4: Create dummy test files ------------
HIGH_ID=$(get_next_id "$HIGHRES_DIR")
LOW_ID=$(get_next_id "$LOWRES_DIR")

HIGH_TXT="${HIGHRES_DIR}/${HIGH_ID}_CAM1_${EPOCH_TIME}.txt"
LOW_TXT="${LOWRES_DIR}/${LOW_ID}_CAM1_${EPOCH_TIME}.txt"

echo "Helloworld High-resolution" > "$HIGH_TXT"
echo "Helloworld Low-resolution" > "$LOW_TXT"

echo "Created:"
echo "  $HIGH_TXT"
echo "  $LOW_TXT"

# ----------- Step 5: Run test_geni2c.py ------------
cd "$TOOLS_DIR" || {
    echo "Error: Cannot change directory to $TOOLS_DIR"
    exit 1
}

echo "Running test_geni2c.py..."
python3 test_geni2c.py
if [ $? -ne 0 ]; then
    echo "Error: test_geni2c.py failed."
    exit 1
fi

# ----------- Step 6: Copy generated files ------------
BIN_FILE="numbers_1_to_100_binary.bin"
TXT_FILE="numbers_1_to_100_text.txt"

if [ -f "$BIN_FILE" ]; then
    HIGH_ID=$(get_next_id "$HIGHRES_DIR")
    LOW_ID=$(get_next_id "$LOWRES_DIR")
    cp "$BIN_FILE" "$HIGHRES_DIR/${HIGH_ID}_CAM1_${EPOCH_TIME}.bin"
    cp "$BIN_FILE" "$LOWRES_DIR/${LOW_ID}_CAM1_${EPOCH_TIME}.bin"
    echo "Copied binary as:"
    echo "  $HIGHRES_DIR/${HIGH_ID}_CAM1_${EPOCH_TIME}.bin"
    echo "  $LOWRES_DIR/${LOW_ID}_CAM1_${EPOCH_TIME}.bin"
else
    echo "Warning: $BIN_FILE not found."
fi

if [ -f "$TXT_FILE" ]; then
    HIGH_ID=$(get_next_id "$HIGHRES_DIR")
    LOW_ID=$(get_next_id "$LOWRES_DIR")
    cp "$TXT_FILE" "$HIGHRES_DIR/${HIGH_ID}_CAM1_${EPOCH_TIME}.txt"
    cp "$TXT_FILE" "$LOWRES_DIR/${LOW_ID}_CAM1_${EPOCH_TIME}.txt"
    echo "Copied text as:"
    echo "  $HIGHRES_DIR/${HIGH_ID}_CAM1_${EPOCH_TIME}.txt"
    echo "  $LOWRES_DIR/${LOW_ID}_CAM1_${EPOCH_TIME}.txt"
else
    echo "Warning: $TXT_FILE not found."
fi

echo "[v] All done!"
