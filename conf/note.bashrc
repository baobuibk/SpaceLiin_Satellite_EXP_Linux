# === Custom Yocto aliases ===
alias devshell='bitbake -c devshell virtual/kernel'
alias cleanstate='bitbake -c cleansstate core-image-satellite'
alias allclean='bitbake -c cleanall core-image-satellite'

# === Custom build automation ===
build() {
    export CUSTOM_IMAGE_BUILD_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "=== Step 1: Cleaning old zip files ==="
    rm -f ~/DownKernel/compulab-nxp-bsp/sources/meta-satellite/recipes-core/custom-files/files/*.zip

    echo "=== Step 2: Zipping source folders ==="
    SRC_DIR=~/DownKernel/source_dev
    DEST_DIR=~/DownKernel/compulab-nxp-bsp/sources/meta-satellite/recipes-core/custom-files/files

    cd "$SRC_DIR" || { echo "Source directory not found!"; return 1; }

    for folder in */; do
        folder_name=$(basename "$folder")
        zip -r "${DEST_DIR}/${folder_name}.zip" "$folder_name"
        echo "Zipped: ${folder_name}.zip"
    done

    echo "=== Step 2.5: Updating custom-time ==="
    echo "$CUSTOM_IMAGE_BUILD_TIME" > "$DEST_DIR/custom-time"
    echo "Updated custom-time to: $CUSTOM_IMAGE_BUILD_TIME"

    echo "=== Step 3: Building Yocto image ==="
    cd ~/DownKernel/compulab-nxp-bsp
    bitbake core-image-satellite
}

#.\uuu.exe --version
#uuu (Universal Update Utility) for nxp imx chips -- libuuu_1.5.233-0-g79ce7d2
#
#Unknown option: --version
#
#.\uuu.exe -v -b emmc_all core-image-satellite-ucm-imx93-20251026053642.rootfs.wic.zst

#
#setenv boot_targets 'usb0 mmc0 mmc1'
#saveenv
#
