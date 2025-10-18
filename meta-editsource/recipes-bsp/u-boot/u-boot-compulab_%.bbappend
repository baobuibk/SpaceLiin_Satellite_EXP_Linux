FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

#SRC_URI += "file://0001_downkernel_uboot_splashchange.patch"
#SRC_URI += "file://0002_downkernel_prevent_eeprom_pca95xx_read.patch"
SRC_URI += "file://0101_downkernel_uboot_splashchange_diseeprom.patch"  
SRC_URI += "file://0102_downkernel_prevent_pca95xx_read.patch"
SRC_URI += "file://0103_downkernel_ubootm33config.patch"

SRC_URI += "file://exp-uboot-config.cfg"

do_configure:prepend() {
    cat ${WORKDIR}/exp-uboot-config.cfg >> ${B}/.config
}
