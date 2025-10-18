import sys
from smbus2 import SMBus

# Default I2C address of PCA9540
I2C_ADDRESS = 0x70

# I2C bus number
I2C_BUS = 7

# Values for each channel (based on PCA9540 control register)
CHANNELS = {
    0: 0x04,  # channel0 enabled (B2 B1 B0 = 1 0 0)
    1: 0x05   # channel1 enabled (B2 B1 B0 = 1 0 1)
}

def switch_channel(bus, channel):
    """Switch to specified I2C channel"""
    if channel not in CHANNELS:
        print(f"Error: Invalid channel {channel}. Must be 0 or 1.", file=sys.stderr)
        return 1  # Return error code
    
    try:
        bus.write_byte(I2C_ADDRESS, CHANNELS[channel])
        print(f"Switched to channel {channel}")
        return 0
    except Exception as e:
        print(f"Error switching channel {channel}: {e}", file=sys.stderr)
        return 2

def disable_all_channels(bus):
    """Disable all channels"""
    try:
        bus.write_byte(I2C_ADDRESS, 0x00)
        print("All channels disabled")
        return 0
    except Exception as e:
        print(f"Error disabling channels: {e}", file=sys.stderr)
        return 2

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pca9540.py <channel>", file=sys.stderr)
        print("  channel: 0 or 1", file=sys.stderr)
        print("Example: python3 pca9540.py 0", file=sys.stderr)
        sys.exit(1)
    
    # Open I2C bus
    try:
        bus = SMBus(I2C_BUS)
    except Exception as e:
        print(f"Error opening I2C bus {I2C_BUS}: {e}", file=sys.stderr)
        sys.exit(3)
    
    exit_code = 0
    try:
        arg = sys.argv[1]
        try:
            channel = int(arg)
            result = switch_channel(bus, channel)
            if result != 0:
                exit_code = result
        except ValueError:
            print(f"Error: '{arg}' is not a valid number.", file=sys.stderr)
            exit_code = 1
    finally:
        bus.close()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
