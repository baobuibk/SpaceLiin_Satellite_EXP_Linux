#!/usr/bin/env python3
from smbus2 import SMBus, i2c_msg
import time
import sys
import string


I2C_BUS = 2
I2C_ADDR = 0x64


def test_with_offset(bus):
    print("\n[-] Testcase: Read WITH setting offset (should work)")

    # Set offset = 0
    offset_bytes = [0x00, 0x00, 0x00, 0x00]
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, offset_bytes))
    print("   Set offset to 0x00000000")

    time.sleep(0.001)

    # Read 16 bytes
    read_msg = i2c_msg.read(I2C_ADDR, 16)
    bus.i2c_rdwr(read_msg)
    data = list(read_msg)

    print(f"   Received: {[f'0x{b:02x}' for b in data]}")
    if data[0:4] == [0x01, 0x00, 0x00, 0x00]:
        print("   [v] Got correct data (number 1 = 0x00000001 little-endian)")


def test_different_offsets(bus):
    print("\n[-] Testcase: Read from different offsets")

    test_offsets = [0, 100, 200, 300, 400, 500]
    for offset in test_offsets:
        offset_bytes = [
            (offset >> 24) & 0xFF,
            (offset >> 16) & 0xFF,
            (offset >> 8) & 0xFF,
            offset & 0xFF
        ]
        bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, offset_bytes))
        time.sleep(0.001)

        read_msg = i2c_msg.read(I2C_ADDR, 8)
        bus.i2c_rdwr(read_msg)
        data = list(read_msg)
        print(f"   Offset {offset:4d}: {[f'0x{b:02x}' for b in data]}")


def hexdump(data, width=16):
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if chr(b) in string.printable and b >= 32 else "." for b in chunk)
        print(f"{i:04x}  {hex_part:<{width*3}}  |{ascii_part}|")


def read_n_bytes(bus, count):
    print(f"\n[.] Reading {count} bytes from I2C addr 0x{I2C_ADDR:02X} ...")

    # Set offset = 0
    offset_bytes = [0x00, 0x00, 0x00, 0x00]
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, offset_bytes))
    time.sleep(0.001)

    # Read data
    read_msg = i2c_msg.read(I2C_ADDR, count)
    bus.i2c_rdwr(read_msg)
    data = list(read_msg)

    hexdump(data)


def main():
    with SMBus(I2C_BUS) as bus:
        if len(sys.argv) == 1:
            print("=" * 60)
            print("Testing I2C Slave Read Protocol")
            print("=" * 60)
            test_with_offset(bus)
            test_different_offsets(bus)
            print("\n" + "=" * 60)

        elif len(sys.argv) == 2:
            try:
                count = int(sys.argv[1])
                if count <= 0:
                    raise ValueError
                read_n_bytes(bus, count)
            except ValueError:
                print("Usage: python3 test_i2c.py [num_bytes]")
                print("Example: python3 test_i2c.py 128")
                sys.exit(1)
        else:
            print("Usage: python3 test_i2c.py [num_bytes]")
            sys.exit(1)


if __name__ == "__main__":
    main()
