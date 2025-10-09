SUMMARY = "Custom files for image"
DESCRIPTION = "Copy custom binaries, scripts, or configs into the image"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/files/common-licenses/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# Source files (relative to files/)
SRC_URI += " \
    file://freertos_hello.elf \
    file://.welcome_steven \
    file://switch_sensor.py \
    file://switch_lane.py \
    file://pin_mux.py \
    file://esat93_note.txt \
    file://banner.sh \
    file://run_m33.sh \
"

inherit allarch

#PN = "file-copier"

# Workdir = where Yocto unpack files
S = "${WORKDIR}"
INHIBIT_SYSROOT_STRIP = "1"

do_install() {
    # copy file into /lib/firmware
    install -d ${D}/lib/firmware
    install -m 0755 ${WORKDIR}/freertos_hello.elf ${D}/lib/firmware

    # copy file into /home/root
    install -d ${D}/home/root
    install -m 0644 ${WORKDIR}/.welcome_steven ${D}/home/root
    install -m 0644 ${WORKDIR}/switch_sensor.py ${D}/home/root
    install -m 0644 ${WORKDIR}/switch_lane.py ${D}/home/root
    install -m 0644 ${WORKDIR}/pin_mux.py ${D}/home/root

    install -m 0644 ${WORKDIR}/esat93_note.txt ${D}/home/root
    install -m 0755 ${WORKDIR}/run_m33.sh ${D}/home/root

    install -d ${D}/home/root/skel_esat93
    install -m 0644 ${WORKDIR}/.welcome_steven ${D}/home/root/skel_esat93
    install -m 0644 ${WORKDIR}/banner.sh ${D}/home/root/skel_esat93
    install -m 0644 ${WORKDIR}/pin_mux.py ${D}/home/root/skel_esat93

    install -d ${D}${sysconfdir}/profile.d
    install -m 0755 ${WORKDIR}/banner.sh ${D}${sysconfdir}/profile.d/
}

# Package out
FILES:${PN} += " \
    /lib/firmware/freertos_hello.elf \
    /home/root/.welcome_steven \
    /home/root/skel_esat93/.welcome_steven \
    /home/root/skel_esat93/banner.sh \
    /home/root/skel_esat93/pin_mux.py \
    /home/root/switch_lane.py \
    /home/root/switch_sensor.py \
    /home/root/pin_mux.py \
    /home/root/esat93_note.txt \
    /home/root/run_m33.sh \
    ${sysconfdir}/profile.d/banner.sh \
"

# Skip some QA warnings
INSANE_SKIP:${PN} += "arch usrmerge"
INSANE_SKIP:${PN}-dbg += "arch usrmerge"
