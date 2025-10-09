SUMMARY = "Disable root autologin on serial-getty"
LICENSE = "MIT"

SRC_URI = ""

do_install() {
    install -d ${D}${sysconfdir}/systemd/system/serial-getty@ttyLP0.service.d
    cat > ${D}${sysconfdir}/systemd/system/serial-getty@ttyLP0.service.d/no-autologin.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty -8 -L %I 115200 $TERM
EOF
}

FILES:${PN} += "${sysconfdir}/systemd/system/serial-getty@ttyLP0.service.d/*"
