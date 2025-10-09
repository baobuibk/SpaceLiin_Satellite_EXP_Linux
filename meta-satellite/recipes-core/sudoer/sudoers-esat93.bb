DESCRIPTION = "Add sudoers config for esat93"
LICENSE = "MIT"

SRC_URI = ""

do_install() {
    install -d ${D}${sysconfdir}/sudoers.d
    echo "esat93 ALL=(ALL) NOPASSWD: ALL" > ${D}${sysconfdir}/sudoers.d/01_esat93
    chmod 0440 ${D}${sysconfdir}/sudoers.d/01_esat93
}

FILES:${PN} += "${sysconfdir}/sudoers.d/01_esat93"
