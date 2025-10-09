#!/bin/bash

GADGET_DIR="/sys/kernel/config/usb_gadget"
GADGET_NAME="g1"
UDC_DEVICE=""

for udc in /sys/class/udc/*; do
    if [ -e "$udc" ]; then
        UDC_DEVICE=$(basename $udc)
        break
    fi
done

if [ -z "$UDC_DEVICE" ]; then
    echo "No UDC device found"
    exit 1
fi

mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config

if [ -d "$GADGET_DIR/$GADGET_NAME" ]; then
    echo "" > "$GADGET_DIR/$GADGET_NAME/UDC" 2>/dev/null || true
    
    # Remove all symlinks
    find "$GADGET_DIR/$GADGET_NAME/configs/" -type l -exec rm {} \; 2>/dev/null || true
    
    # Remove functions
    rmdir "$GADGET_DIR/$GADGET_NAME/functions/"* 2>/dev/null || true
    
    # Remove configs
    rmdir "$GADGET_DIR/$GADGET_NAME/configs/"*/strings/* 2>/dev/null || true
    rmdir "$GADGET_DIR/$GADGET_NAME/configs/"* 2>/dev/null || true
    
    # Remove strings
    rmdir "$GADGET_DIR/$GADGET_NAME/strings/"* 2>/dev/null || true
    
    # Remove gadget
    rmdir "$GADGET_DIR/$GADGET_NAME" 2>/dev/null || true
fi

mkdir -p "$GADGET_DIR/$GADGET_NAME"
cd "$GADGET_DIR/$GADGET_NAME"

echo 0x1d6b > idVendor  # Linux Foundation
echo 0x0104 > idProduct # Multifunction Composite Gadget
echo 0x0100 > bcdDevice # v1.0.0
echo 0x0200 > bcdUSB    # USB 2.0

echo 0x02 > bDeviceClass
echo 0x00 > bDeviceSubClass
echo 0x00 > bDeviceProtocol

mkdir -p strings/0x409
echo "1234567890abcdef" > strings/0x409/serialnumber
echo "SLT" > strings/0x409/manufacturer
echo "UCM-iMX93 CDC Serial" > strings/0x409/product

mkdir -p configs/c.1/strings/0x409
echo "CDC ACM Config" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower
echo 0x80 > configs/c.1/bmAttributes  # Bus powered

mkdir -p functions/acm.GS0

ln -s functions/acm.GS0 configs/c.1/

sleep 1
echo "$UDC_DEVICE" > UDC

echo "USB CDC ACM Gadget configured successfully"
echo "Virtual COM port available at: /dev/ttyGS0"
echo "UDC Device: $UDC_DEVICE"

if [ -e /dev/ttyGS0 ]; then
    stty -F /dev/ttyGS0 115200 cs8 -cstopb -parenb
    echo "Serial port configured: 115200 8N1"
fi
