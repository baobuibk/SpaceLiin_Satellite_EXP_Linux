SUMMARY = "Pre-generated SSH host keys"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit allarch

DEPENDS = "openssl-native"

do_install() {
    install -d ${D}${sysconfdir}/ssh

    # RSA key
    openssl genrsa -out ${D}${sysconfdir}/ssh/ssh_host_rsa_key 2048
    openssl rsa -in ${D}${sysconfdir}/ssh/ssh_host_rsa_key -pubout > ${D}${sysconfdir}/ssh/ssh_host_rsa_key.pub

    # ECDSA key
    openssl ecparam -name prime256v1 -genkey -noout -out ${D}${sysconfdir}/ssh/ssh_host_ecdsa_key
    openssl ec -in ${D}${sysconfdir}/ssh/ssh_host_ecdsa_key -pubout > ${D}${sysconfdir}/ssh/ssh_host_ecdsa_key.pub

    # ED25519 key
    openssl genpkey -algorithm ed25519 -out ${D}${sysconfdir}/ssh/ssh_host_ed25519_key
    openssl pkey -in ${D}${sysconfdir}/ssh/ssh_host_ed25519_key -pubout > ${D}${sysconfdir}/ssh/ssh_host_ed25519_key.pub

    chmod 600 ${D}${sysconfdir}/ssh/ssh_host_*_key
    chmod 644 ${D}${sysconfdir}/ssh/ssh_host_*_key.pub
}

FILES:${PN} = "${sysconfdir}/ssh/ssh_host_*"
RDEPENDS:${PN} = "openssh"
