SUMMARY = "First boot setup (copy skel to user homes once)"
DESCRIPTION = "Run once at first boot to distribute files under /home/root/skel_* to users"
LICENSE = "CLOSED"

SRC_URI += "file://firstboot.sh \
            file://firstboot.service"

S = "${WORKDIR}"

inherit systemd

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/firstboot.service ${D}${systemd_system_unitdir}/firstboot.service

    install -d ${D}/usr/sbin
    install -m 0755 ${WORKDIR}/firstboot.sh ${D}/usr/sbin/firstboot.sh
}

SYSTEMD_SERVICE:${PN} = "firstboot.service"
SYSTEMD_AUTO_ENABLE = "enable"

FILES:${PN} += "${systemd_system_unitdir}/firstboot.service /usr/sbin/firstboot.sh"
