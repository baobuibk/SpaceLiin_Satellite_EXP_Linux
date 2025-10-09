#!/usr/bin/env python3
import sys
from smbus2 import SMBus

I2C_ADDR = 0x20

I2C_BUS = 7

OUTPUT_PORT0 = 0x02
OUTPUT_PORT1 = 0x03
CONFIG_PORT0 = 0x06
CONFIG_PORT1 = 0x07

def set_pin(bus, pin, value):
    if not (0 <= pin <= 15):
        print("Error: IO must be in range 0-15")
        sys.exit(1)

    port = 0 if pin < 8 else 1
    bit = pin % 8

    cfg_reg = CONFIG_PORT0 if port == 0 else CONFIG_PORT1
    out_reg = OUTPUT_PORT0 if port == 0 else OUTPUT_PORT1

    cfg = bus.read_byte_data(I2C_ADDR, cfg_reg)
    out = bus.read_byte_data(I2C_ADDR, out_reg)

    cfg &= ~(1 << bit)
    bus.write_byte_data(I2C_ADDR, cfg_reg, cfg)

    if value:
        out |= (1 << bit)
    else:
        out &= ~(1 << bit)
    bus.write_byte_data(I2C_ADDR, out_reg, out)

    print(f"Set IO{pin} to {value} (port {port}, bit {bit})")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 pinmux.py [io_number 0-15] [level 0|1]")
        sys.exit(1)

    pin = int(sys.argv[1])
    value = int(sys.argv[2])

    with SMBus(I2C_BUS) as bus:
        set_pin(bus, pin, value)
