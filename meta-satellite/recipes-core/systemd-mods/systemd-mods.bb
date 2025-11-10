DESCRIPTION = "Enable Modules autoload"
LICENSE = "CLOSED"
SRC_URI = ""

do_install() {
    # File usb-gadget.conf
    install -d ${D}${sysconfdir}/modules-load.d
    echo "libcomposite"    >  ${D}${sysconfdir}/modules-load.d/usb-gadget.conf
    echo "usb_f_rndis"     >> ${D}${sysconfdir}/modules-load.d/usb-gadget.conf
    echo "usb_f_ecm"       >> ${D}${sysconfdir}/modules-load.d/usb-gadget.conf
    echo "g_ether"         >> ${D}${sysconfdir}/modules-load.d/usb-gadget.conf

    # File camera.conf
    echo "tca6416-sensor"  >  ${D}${sysconfdir}/modules-load.d/csi-camera.conf
    echo "pca9544-switch"  >> ${D}${sysconfdir}/modules-load.d/csi-camera.conf
    echo "ar2020"          >> ${D}${sysconfdir}/modules-load.d/csi-camera.conf
    echo "imx8-media-dev"  >> ${D}${sysconfdir}/modules-load.d/csi-camera.conf

    # File can.conf
    echo "can-dev"         >  ${D}${sysconfdir}/modules-load.d/can.conf
    echo "can-raw"         >> ${D}${sysconfdir}/modules-load.d/can.conf
    echo "can-bcm"         >> ${D}${sysconfdir}/modules-load.d/can.conf
    echo "flexcan"         >> ${D}${sysconfdir}/modules-load.d/can.conf

    # File i2c-slave.conf
    echo "exprom"          >  ${D}${sysconfdir}/modules-load.d/i2c-slave.conf

    # File rpmsg.conf
    # echo "imx_rpmsg_hybrid" > ${D}${sysconfdir}/modules-load.d/rpmsg.conf
}

#do_install() {
#    install -d ${D}${sysconfdir}/modules-load.d
#    
#    echo "libcomposite" > ${D}${sysconfdir}/modules-load.d/usb-gadget.conf
#    echo "usb_f_acm" >> ${D}${sysconfdir}/modules-load.d/usb-gadget.conf
#}

FILES:${PN} += "${sysconfdir}/modules-load.d/usb-gadget.conf"
FILES:${PN} += "${sysconfdir}/modules-load.d/csi-camera.conf"
FILES:${PN} += "${sysconfdir}/modules-load.d/can.conf"
FILES:${PN} += "${sysconfdir}/modules-load.d/i2c-slave.conf"
# FILES:${PN} += "${sysconfdir}/modules-load.d/rpmsg.conf"
