#!/usr/bin/env python3
import sys
import time
import binascii
from smbus2 import SMBus, i2c_msg

I2C_BUS = 4
I2C_ADDR = 0x64


def hexdump_with_ascii(data):
    """Display data in hex + ASCII format"""
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"{i:08X}  {hex_part:<47}  |{ascii_part}|")


def crc32_isohdlc(data: bytes) -> int:
    """
    Calculate CRC32 using ISO-HDLC standard
    (polynomial 0x04C11DB7, init=0xFFFFFFFF, xorout=0xFFFFFFFF)
    No reflection on input/output.
    """
    poly = 0x04C11DB7
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) & 0xFFFFFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <num_bytes_to_read>")
        sys.exit(1)

    num_bytes = int(sys.argv[1])
    if num_bytes <= 0:
        print("[x] Number of bytes must be greater than 0")
        sys.exit(1)

    print("=" * 60)
    print(f"Reading {num_bytes} bytes from I2C address 0x{I2C_ADDR:02X} on bus {I2C_BUS}")
    print("=" * 60)

    with SMBus(I2C_BUS) as bus:
        read_msg = i2c_msg.read(I2C_ADDR, num_bytes)
        bus.i2c_rdwr(read_msg)
        data = bytes(list(read_msg))

    print("\nDATA DUMP:")
    hexdump_with_ascii(data)

    crc = crc32_isohdlc(data)
    print("\nCRC32 (ISO-HDLC): 0x%08X" % crc)
    print("=" * 60)


if __name__ == "__main__":
    main()
