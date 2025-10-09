SUMMARY = "Custom systemd service and usb0 static network setup"
LICENSE = "CLOSED"

SRC_URI += " \
    file://10-usb0.network \
    file://startup.sh \
    file://startup.service \
"

S = "${WORKDIR}"

inherit systemd

SYSTEMD_SERVICE:${PN} = "startup.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    # --- Network config ---
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${WORKDIR}/10-usb0.network ${D}${sysconfdir}/systemd/network/

    # --- Service file ---
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/startup.service ${D}${systemd_system_unitdir}/

    # --- Script ---
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/startup.sh ${D}${bindir}/
}

FILES:${PN} += " \
    ${sysconfdir}/systemd/network/10-usb0.network \
    ${systemd_system_unitdir}/startup.service \
    ${bindir}/startup.sh \
"
