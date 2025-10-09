DESCRIPTION = "USB CDC ACM Gadget Configuration"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/files/common-licenses/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"


SRC_URI = "file://usb-gadget-setup.sh \
           file://usb-gadget.service"

inherit systemd

SYSTEMD_SERVICE:${PN} = "usb-gadget.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/usb-gadget-setup.sh ${D}${bindir}/
    
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/usb-gadget.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} += "${bindir}/usb-gadget-setup.sh"
RDEPENDS:${PN} += "bash"
