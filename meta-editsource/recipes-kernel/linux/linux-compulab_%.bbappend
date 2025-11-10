FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

#SRC_URI += " \
#    file://0001-dts-change-include-esat93-dtsi.patch \
#    file://0002-source-change-dwc-mipi-csi2-2mods-DT-RAW10.patch \
#    file://0003-source-change-imx8-isi-fmt-1mods-BA10.patch \
#    file://0004-source-change-imx8-isi-hw-2mods-chainbuf.patch \
#    file://0005-source-change-imx8-isi-cap-2mods-default-input-SBGGR10.patch \
#    file://0007-source-change-imx8-mipi-csi2-1mods-MEDIA_BUS_FMT_SBGGR10_1X10.patch \
#    file://0008-source-change-3mods-Kconfig-Makefile-compulabconfig.patch \
#    file://0009-source-change-imx8-isi-cap-3mods-SRGB-to-RAW.patch \
#    file://0010-source-change-dwc-mipi-csi2-add-test-log.patch \
#    file://0011-source-change-debug-hw-mipicsi-mipcsisam.patch \
#    file://0012_test_removedwc.patch \
#"


SRC_URI += " \
    file://0001-dts-change-include-esat93-dtsi.patch \
    file://0201_downkernel6155_editsource_kconfig_makefile.patch \
    file://0200_downkernel6155_editsource_fmt.patch \
    file://0202_downkernel_changing_from_ref_github.patch \
    file://0203_downkernel_chainbuf_fix.patch \
    file://0204_downkernel_switchlaneswitchsensor_kconfigmakefile.patch \
    file://0205_downkernel_KconfigMakefile_for_exprom_i2cslave.patch \
    file://0206_downkernel_KconfigMakefile_for_rpmsg_hybrid.patch \
    file://9998_downkernel_fix_limit4096.patch \ 
"

