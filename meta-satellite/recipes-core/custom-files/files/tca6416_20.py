#!/usr/bin/env python3
"""
TCA6416A GPIO Controller
Usage:
    python3 tca6416.py <pin> <value>  - Set pin to 0 or 1
    python3 tca6416.py clear          - Clear all pins to 0
    python3 tca6416.py status         - Show current state of all pins

Examples:
    python3 tca6416.py 0 1    # Set P00 to HIGH
    python3 tca6416.py 15 0   # Set P17 to LOW
    python3 tca6416.py clear  # Set all pins to LOW
"""

import sys
import smbus2

I2C_BUS = 6
I2C_ADDRESS = 0x20

REG_INPUT_PORT0 = 0x00
REG_INPUT_PORT1 = 0x01
REG_OUTPUT_PORT0 = 0x02
REG_OUTPUT_PORT1 = 0x03
REG_POLARITY_PORT0 = 0x04
REG_POLARITY_PORT1 = 0x05
REG_CONFIG_PORT0 = 0x06  # 0 = output, 1 = input
REG_CONFIG_PORT1 = 0x07


class TCA6416A:
    
    def __init__(self, bus_num=I2C_BUS, address=I2C_ADDRESS):
        self.bus = smbus2.SMBus(bus_num)
        self.address = address
        self._init_device()
    
    def _init_device(self):
        try:
            self.bus.write_byte_data(self.address, REG_OUTPUT_PORT0, 0x00)
            self.bus.write_byte_data(self.address, REG_OUTPUT_PORT1, 0x00)
            self.bus.write_byte_data(self.address, REG_CONFIG_PORT0, 0x00)
            self.bus.write_byte_data(self.address, REG_CONFIG_PORT1, 0x00)
        except Exception as e:
            print(f"Error initializing device: {e}")
            sys.exit(1)
    
    def set_pin(self, pin_num, value):
        """
        pin_num: 0-15 (0-7: Port0, 8-15: Port1)
        value: 0 hoặc 1
        """
        if pin_num < 0 or pin_num > 15:
            raise ValueError("Pin number must be 0-15")
        
        if value not in [0, 1]:
            raise ValueError("Value must be 0 or 1")
        
        if pin_num < 8:
            port_reg = REG_OUTPUT_PORT0
            bit_pos = pin_num
        else:
            port_reg = REG_OUTPUT_PORT1
            bit_pos = pin_num - 8
        
        current_value = self.bus.read_byte_data(self.address, port_reg)
        
        mask = 1 << bit_pos
        if value == 1:
            new_value = current_value | mask  # Set bit
        else:
            new_value = current_value & ~mask  # Clear bit
        
        self.bus.write_byte_data(self.address, port_reg, new_value)
        
        pin_name = f"P{pin_num//8}{pin_num%8}"
        print(f"Set {pin_name} (pin {pin_num}) = {value}")
    
    def clear_all(self):
        self.bus.write_byte_data(self.address, REG_OUTPUT_PORT0, 0x00)
        self.bus.write_byte_data(self.address, REG_OUTPUT_PORT1, 0x00)
        print("All pins cleared to 0")
    
    def get_status(self):
        port0_out = self.bus.read_byte_data(self.address, REG_OUTPUT_PORT0)
        port1_out = self.bus.read_byte_data(self.address, REG_OUTPUT_PORT1)
        
        print("\nCurrent GPIO Status:")
        print("=" * 40)
        print("Port 0 (P00-P07):")
        for i in range(8):
            value = (port0_out >> i) & 1
            print(f"  P0{i} (pin {i:2d}): {value}")
        
        print("\nPort 1 (P10-P17):")
        for i in range(8):
            value = (port1_out >> i) & 1
            print(f"  P1{i} (pin {i+8:2d}): {value}")
        print("=" * 40)
    
    def close(self):
        self.bus.close()


def print_usage():
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        tca = TCA6416A()
        
        if command == "clear":
            tca.clear_all()
        
        elif command == "status":
            tca.get_status()
        
        elif command == "help" or command == "-h" or command == "--help":
            print_usage()
        
        else:
            if len(sys.argv) != 3:
                print("Error: Pin set command requires pin number and value")
                print_usage()
                sys.exit(1)
            
            try:
                pin_num = int(sys.argv[1])
                value = int(sys.argv[2])
                tca.set_pin(pin_num, value)
            except ValueError as e:
                print(f"Error: {e}")
                print_usage()
                sys.exit(1)
        
        tca.close()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
