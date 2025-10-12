#!/bin/sh
echo "[Startup] System booted at $(date)" >> /var/log/startup.log
# /usr/bin/python3 /home/root/app.py &
cat /home/root/.welcome_steven > /dev/ttyLP0
ifconfig usb0 192.168.6.7 netmask 255.255.255.0 up
ip link set can0 down
ip link set can1 down
ip link set can0 up type can bitrate 500000
ip link set can1 up type can bitrate 500000
ip link set can0 up
ip link set can1 up
gpioset -c gpiochip2 --daemonize 26=1
