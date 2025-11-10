DESCRIPTION = "Satellite production image for i.MX93 \
Minimal, no GUI, includes devtools, Python, minicom, \
and USB Ethernet gadget support."
LICENSE = "MIT"

inherit core-image

IMAGE_FEATURES += " \
    ssh-server-openssh \
    package-management \
"

IMAGE_FEATURES:remove = "debug-tweaks"
EXTRA_IMAGE_FEATURES:remove = "debug-tweaks"
IMAGE_FEATURES:remove = "serial-autologin-root"
EXTRA_IMAGE_FEATURES:remove = "serial-autologin-root"

# IMAGE_FEATURES += "read-only-rootfs"

CORE_IMAGE_EXTRA_INSTALL += " \
    nano \
    minicom \
    python3 \
    python3-pip \
    python3-smbus2 \
    python3-can \
    python3-cantools \
    python3-gpiod \
    python3-pyserial \ 
    python3-spidev \
    python3-venv \
    python3-supervisor \
    python3-numpy \
    python3-pillow \
    python3-tkinter \
    tk \
    tcl \
    gcc \
    g++ \
    make \
    gdb \
    i2c-tools \
    can-utils \
    usbutils \
    ethtool \
    iproute2 \
    net-tools \
    htop \
    vim \
    tree \
    lrzsz \
    devmem2 \
    socat \
    zeromq \
    python3-pyzmq \
    kernel-modules \
"
# WEBSERVER
#--------------------------------------------
IMAGE_INSTALL:append = " \
    python3-flask \
    python3-flask-cors \
    python3-werkzeug \
    python3-jinja2 \
    python3-markupsafe \
    python3-itsdangerous \
    python3-click \
"

IMAGE_INSTALL:append = " python3-gunicorn "

IMAGE_INSTALL:append = " \
    curl \
"

# GUI
# --------------------------------------------
IMAGE_FEATURES += " x11-base x11 "

CORE_IMAGE_EXTRA_INSTALL += " \
    xserver-xorg \
    xterm \
    xauth \
    xclock \
    xinit \
    xhost \
    xmessage \
    xsetroot \
    twm \
    gtk+3-demo \
    gdk-pixbuf \
    feh \
    imagemagick \
"

# ====== Python GUI Support ======
IMAGE_INSTALL:append = " \
    python3-pygobject \
"

# ====== GStreamer (Full IMX Stack) ======
IMAGE_INSTALL:append = " \
    packagegroup-fsl-gstreamer1.0-full \
    gstreamer1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
"

# --------------------------------------------

CORE_IMAGE_EXTRA_INSTALL += " lshw procps util-linux lsb-release "
CORE_IMAGE_EXTRA_INSTALL += " v4l-utils "
CORE_IMAGE_EXTRA_INSTALL += " systemd-mods "
CORE_IMAGE_EXTRA_INSTALL += " systemd-serial-no-autologin "
CORE_IMAGE_EXTRA_INSTALL += " systemd-analyze "
CORE_IMAGE_EXTRA_INSTALL += " sudoers-esat93 "

IMAGE_INSTALL:append = " libsocketcan libsocketcan-dev python3-dev binutils "
IMAGE_INSTALL:append = " zip unzip "
IMAGE_INSTALL:append = " e2fsprogs-resize2fs "
IMAGE_INSTALL:append = " sqlite3 python3-sqlite3 "

IMAGE_FEATURES:remove = "read-only-rootfs"

IMAGE_INSTALL:append = " udev-perms "
IMAGE_INSTALL:append = " gstreamer1.0 "

SYSTEMD_SERVICE_MASK:pn-ModemManager = "ModemManager.service"
SYSTEMD_SERVICE_MASK:pn-ofono = "ofono.service"

IMAGE_INSTALL:append = " custom-files "

IMAGE_INSTALL += "openssh-host-keys"

IMAGE_INSTALL:append = " firstboot "
IMAGE_INSTALL:append = " startup-scripts "
IMAGE_INSTALL:append = " service-systemd "
IMAGE_INSTALL:append = " grow-fs "

#IMAGE_INSTALL += "usb-gadget-config"
