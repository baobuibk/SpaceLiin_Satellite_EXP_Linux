SUMMARY = "Custom startup scripts (run on boot)"
DESCRIPTION = "Installs a startup script + systemd unit which runs on each boot"
LICENSE = "CLOSED"

SRC_URI += " \
    file://startup-scripts.sh \
    file://temp-logger.sh \
    file://startup-scripts.service \
"

S = "${WORKDIR}"

inherit systemd

SYSTEMD_SERVICE:${PN} = "startup-scripts.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    # --- Scripts ---
    install -d ${D}${bindir}/scripts.d
    install -m 0755 ${WORKDIR}/startup-scripts.sh ${D}${bindir}/scripts.d/startup-scripts.sh
    install -m 0755 ${WORKDIR}/temp-logger.sh ${D}${bindir}/scripts.d/temp-logger.sh

    # --- Systemd unit ---
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/startup-scripts.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} += " \
    ${bindir}/scripts.d/startup-scripts.sh \
    ${bindir}/scripts.d/temp-logger.sh \
    ${systemd_system_unitdir}/startup-scripts.service \
"
