#!/bin/sh
echo "[Startup] System booted at $(date)" >> /var/log/startup.log
# /usr/bin/python3 /home/root/app.py &
cat /home/root/.welcome_steven > /dev/ttyLP0
ifconfig usb0 192.168.6.7 netmask 255.255.255.0 up
ip link set can0 down
ip link set can1 down
ip link set dev can0 down
ip link set dev can0 up type can bitrate 1000000 restart-ms 100
ip link set dev can0 txqueuelen 100
ip link set dev can1 down
ip link set dev can1 up type can bitrate 1000000 restart-ms 100
ip link set dev can1 txqueuelen 100
ip link set can0 up
ip link set can1 up
gpioset -t0 -c gpiochip2 26=1
gpioset -t0 -c gpiochip2 18=1
gpioset -t0 -c gpiochip0 17=1
gpioset -t0 -c gpiochip1 20=0
gpioset -t0 -c gpiochip1 22=1
gpioset -t0 -c gpiochip1 21=0
gpioset -t0 -c gpiochip1 24=0
modprobe -r imx_rpmsg_hybrid
