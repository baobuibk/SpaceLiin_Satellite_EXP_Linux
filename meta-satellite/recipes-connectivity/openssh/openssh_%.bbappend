do_install:append() {
    # Remove sshdgenkeys service since we provide pre-built keys
    rm -f ${D}${systemd_system_unitdir}/sshdgenkeys.service
    rm -f ${D}${systemd_system_unitdir}/multi-user.target.wants/sshdgenkeys.service
}
