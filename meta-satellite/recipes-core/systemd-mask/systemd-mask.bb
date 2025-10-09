DESCRIPTION = "Mask unwanted systemd services"
LICENSE = "MIT"

inherit allarch

do_install() {
    install -d ${D}${systemd_system_unitdir}
    ln -sf /dev/null ${D}${systemd_system_unitdir}/ModemManager.service
    ln -sf /dev/null ${D}${systemd_system_unitdir}/ofono.service
}
FILES:${PN} = "${systemd_system_unitdir}/*"
