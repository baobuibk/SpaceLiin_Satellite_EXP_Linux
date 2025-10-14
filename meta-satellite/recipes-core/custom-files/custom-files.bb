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
    file://setup.sh \
    file://run.sh \
    file://libcsp.zip;unpack=no \
    file://test_geni2c.py \
    file://modfsp.py \
    file://tca6416.py \
    file://test_i2c.py \
    file://pwm_control.py \
    file://custom-time \
"

inherit allarch

#PN = "file-copier"

# Workdir = where Yocto unpack files
S = "${WORKDIR}"
INHIBIT_SYSROOT_STRIP = "1"

do_install() {
    # copy file into /lib/firmware
    # install -d ${D}/lib/firmware
    # install -m 0755 ${WORKDIR}/freertos_hello.elf ${D}/lib/firmware
    # Create home folder structure
    install -d ${D}/home/root
    install -d ${D}/home/root/.a55_src/00_src
    install -d ${D}/home/root/.a55_src/01_data
    install -d ${D}/home/root/.a55_src/97_conf
    install -d ${D}/home/root/.a55_src/98_boot
    install -d ${D}/home/root/.a55_src/99_log

    install -d ${D}/home/root/.m33_src/00_src
    install -d ${D}/home/root/.m33_src/01_fw

    install -d ${D}/home/root/tmp
    install -m 0755 ${WORKDIR}/libcsp.zip ${D}/home/root/tmp

    install -d ${D}/home/root/tools
    # Copy main text files
    install -m 0644 ${WORKDIR}/.welcome_steven ${D}/home/root
    install -m 0644 ${WORKDIR}/esat93_note.txt ${D}/home/root
    # Copy FreeRTOS ELF into .m33_src
    install -m 0755 ${WORKDIR}/freertos_hello.elf ${D}/home/root/.m33_src/01_fw/
 

    # Copy tools
    install -m 0755 ${WORKDIR}/switch_sensor.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/switch_lane.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/pin_mux.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/test_geni2c.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/modfsp.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/tca6416.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/test_i2c.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/pwm_control.py ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/setup.sh ${D}/home/root/tools/
    install -m 0755 ${WORKDIR}/run.sh ${D}/home/root/tools/
    

    # copy file into /home/root
    install -m 0755 ${WORKDIR}/run_m33.sh ${D}/home/root

    install -d ${D}/home/root/skel_bee
    install -m 0644 ${WORKDIR}/.welcome_steven ${D}/home/root/skel_bee
    install -m 0644 ${WORKDIR}/banner.sh ${D}/home/root/skel_bee
    install -m 0644 ${WORKDIR}/pin_mux.py ${D}/home/root/skel_bee

    install -d ${D}${sysconfdir}/profile.d
    install -m 0755 ${WORKDIR}/banner.sh ${D}${sysconfdir}/profile.d/   
    install -m 0644 ${WORKDIR}/custom-time ${D}${sysconfdir}/custom-time

}

FILES:${PN} += " \
    /home/root/.welcome_steven \
    /home/root/esat93_note.txt \
    /home/root/.a55_src/00_src \
    /home/root/.a55_src/01_data \
    /home/root/.a55_src/97_conf \
    /home/root/.a55_src/98_boot \
    /home/root/.a55_src/99_log \
    /home/root/.m33_src/00_src \
    /home/root/.m33_src/01_fw/freertos_hello.elf \
    /home/root/tmp/libcsp.zip \
    /home/root/tools/switch_sensor.py \
    /home/root/tools/switch_lane.py \
    /home/root/tools/pin_mux.py \
    /home/root/tools/test_geni2c.py \
    /home/root/tools/modfsp.py \
    /home/root/tools/tca6416.py \
    /home/root/tools/test_i2c.py \
    /home/root/tools/pwm_control.py \
    /home/root/tools/setup.sh \
    /home/root/tools/run.sh \
    /home/root/skel_bee/.welcome_steven \
    /home/root/skel_bee/banner.sh \
    /home/root/skel_bee/pin_mux.py \
    /home/root/run_m33.sh \
    ${sysconfdir}/profile.d/banner.sh \
    ${sysconfdir}/custom-time \
"

# Skip some QA warnings
INSANE_SKIP:${PN} += "arch usrmerge"
INSANE_SKIP:${PN}-dbg += "arch usrmerge"
