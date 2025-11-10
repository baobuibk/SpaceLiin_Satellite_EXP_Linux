#!/bin/bash
set -e 

# -----------------------------
# CONFIG
# -----------------------------
DEV_ROOT="$(pwd)"   
BUILD_DIR="$DEV_ROOT/00_Dev16/DevBuild"
LIBCSP_PATH="$DEV_ROOT/00_Dev16/DevSrc"

# -----------------------------
# STEP 1: Setup environment
# -----------------------------
if [ ! -f "$BUILD_DIR/.setup_done" ]; then
    echo "[INFO] Running setup for the first time..."
    sudo ln -sf /usr/bin/python3 /usr/bin/python
    echo "[INFO] Linking python3 → python done."
    mkdir -p "$BUILD_DIR"
    touch "$BUILD_DIR/.setup_done"
else
    echo "[INFO] Setup already done for this session."
fi

# -----------------------------
# STEP 2: Run waf configure
# -----------------------------
echo "[INFO] Configuring Waf output directory: $BUILD_DIR"
# -----------------------------
# STEP 3: Set environment for build
# -----------------------------
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$LIBCSP_PATH"
#export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:($PWD)"
echo "[INFO] LD_LIBRARY_PATH set to: $LD_LIBRARY_PATH"

# -----------------------------
# STEP 4: Run Python build script
# -----------------------------
echo "[INFO] Starting dev_buildall.py..."
python3 "$DEV_ROOT/00_Dev16/dev_buildall.py"

cp ./build/* 00_Dev16/DevBuild/ -r
cp ./build/libcsp* 00_Dev16/DevSrc/ -r

echo "[SUCCESS] Build completed successfully!"
