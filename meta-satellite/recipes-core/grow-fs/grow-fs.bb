SUMMARY = "First-boot data partition creator/expander (p3 -> /data)"
DESCRIPTION = "On first boot, create/expand mmc p3, format ext4 (LABEL=DATA), add fstab, mount /data, and resize filesystem."
LICENSE = "CLOSED"

inherit systemd

SRC_URI = " \
    file://grow-fs.sh \
    file://grow-fs.service \
"

S = "${WORKDIR}"

# - util-linux: sfdisk, partx, findmnt, blockdev
# - e2fsprogs-resize2fs: resize2fs
# - e2fsprogs-mke2fs: mkfs.ext4
# - e2fsprogs-e2fsck: e2fsck
# - udev: udevadm
RDEPENDS:${PN} = "util-linux e2fsprogs-resize2fs e2fsprogs-mke2fs e2fsprogs-e2fsck udev"

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/grow-fs.service ${D}${systemd_system_unitdir}/grow-fs.service

    install -d ${D}${sbindir}
    install -m 0755 ${WORKDIR}/grow-fs.sh ${D}${sbindir}/grow-fs.sh
}

SYSTEMD_SERVICE:${PN} = "grow-fs.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

FILES:${PN} += " \
  ${systemd_system_unitdir}/grow-fs.service \
  ${sbindir}/grow-fs.sh \
"
