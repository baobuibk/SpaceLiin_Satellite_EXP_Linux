DESCRIPTION = "Add sudoers config for bee"
LICENSE = "MIT"

SRC_URI = ""

do_install() {
    install -d ${D}${sysconfdir}/sudoers.d
    echo "bee ALL=(ALL) NOPASSWD: ALL" > ${D}${sysconfdir}/sudoers.d/01_bee
    chmod 0440 ${D}${sysconfdir}/sudoers.d/01_bee
}

FILES:${PN} += "${sysconfdir}/sudoers.d/01_bee"
