FILESEXTRAPATHS:prepend := "${THISDIR}/linux-compulab:"

#KERNEL_DEVICETREE:append = " compulab/ucm-imx93-satellite.dtb"
#UBOOT_DTB_NAME:ucm-imx93 = "ucm-imx93-satellite.dtb"

#KERNEL_CONFIG = "ucm-imx93_defconfig"

#SRC_URI += "file://0001-arm64-dts-compulab-add-ucm-imx93-satellite.dts.patch"
SRC_URI += "file://compulab/esat93.dtsi"
#SRC_URI += "file://ucm-imx93_defconfig"
SRC_URI += "file://ar2020.c"
SRC_URI += "file://pca9544-switch.c"
SRC_URI += "file://tca6416-sensor.c"
SRC_URI += "file://ar2020.cfg"
SRC_URI += "file://compulab/ucm-imx93-lvds.dts"
SRC_URI += "file://exprom.c"

KERNEL_CONFIG_FRAGMENTS += "ar2020.cfg"

do_configure:append() {
    rm -f ${S}/arch/arm64/boot/dts/compulab/esat93.dtsi

    rm -f ${S}/arch/arm64/boot/dts/compulab/ucm-imx93-lvds.dts

    cp ${WORKDIR}/compulab/esat93.dtsi \
       ${S}/arch/arm64/boot/dts/compulab/esat93.dtsi

    cp ${WORKDIR}/compulab/ucm-imx93-lvds.dts \
		${S}/arch/arm64/boot/dts/compulab/ucm-imx93-lvds.dts

    cp ${WORKDIR}/ar2020.c ${S}/drivers/media/i2c/
   
    cp ${WORKDIR}/pca9544-switch.c ${S}/drivers/media/i2c/

    cp ${WORKDIR}/tca6416-sensor.c ${S}/drivers/media/i2c/

    cp ${WORKDIR}/exprom.c ${S}/drivers/i2c/
}

#do_configure:prepend() {
#    cp ${WORKDIR}/ucm-imx93_defconfig \
#       ${S}/arch/arm64/configs/ucm-imx93_defconfig
#}

