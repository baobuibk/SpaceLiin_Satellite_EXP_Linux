#!/usr/bin/env python3
import struct
import sys

def create_number_file_text(filename, start=1, end=100):
    with open(filename, 'w') as f:
        for i in range(start, end + 1):
            f.write(f"{i}\n")
    
    size = open(filename, 'rb').read().__len__()
    print(f"✓ Created: {filename}")
    print(f"  Format: Text, one number per line")
    print(f"  Size: {size} bytes")
    print(f"  Content: {start} to {end}")
    return size

def create_number_file_binary(filename, start=1, end=100):
    with open(filename, 'wb') as f:
        for i in range(start, end + 1):
            f.write(struct.pack('<I', i))
    
    size = open(filename, 'rb').read().__len__()
    print(f"✓ Created: {filename}")
    print(f"  Format: Binary uint32_t (little-endian)")
    print(f"  Size: {size} bytes ({end - start + 1} numbers × 4 bytes)")
    print(f"  Content: {start} to {end}")
    return size

def create_pattern_file(filename, pattern_type='sequential', size_kb=10):
    import random
    
    size_bytes = size_kb * 1024
    
    with open(filename, 'wb') as f:
        if pattern_type == 'sequential':
            # Pattern: 0x00, 0x01, 0x02, ..., 0xFF, 0x00, 0x01, ...
            data = bytes([i % 256 for i in range(size_bytes)])
            f.write(data)
            
        elif pattern_type == 'random':
            # Pattern: Random bytes
            data = bytes([random.randint(0, 255) for _ in range(size_bytes)])
            f.write(data)
            
        elif pattern_type == 'alternating':
            # Pattern: 0xAA, 0x55, 0xAA, 0x55, ...
            data = bytes([0xAA if i % 2 == 0 else 0x55 for i in range(size_bytes)])
            f.write(data)
    
    print(f"✓ Created: {filename}")
    print(f"  Format: Binary pattern ({pattern_type})")
    print(f"  Size: {size_bytes} bytes ({size_kb} KB)")
    return size_bytes

def create_structured_file(filename):
    with open(filename, 'wb') as f:
        # Header (16 bytes)
        magic = b'TEST'
        version = struct.pack('<I', 1)
        num_entries = struct.pack('<I', 100)
        reserved = struct.pack('<I', 0)
        f.write(magic + version + num_entries + reserved)
        
        # Data: 100 entries, entry 8 bytes (index + value)
        for i in range(1, 101):
            index = struct.pack('<I', i)
            value = struct.pack('<I', i * 100)  # value = index * 100
            f.write(index + value)
    
    size = open(filename, 'rb').read().__len__()
    print(f"✓ Created: {filename}")
    print(f"  Format: Structured binary")
    print(f"  Size: {size} bytes")
    print(f"  Header: 16 bytes")
    print(f"  Data: 100 entries × 8 bytes = 800 bytes")
    print(f"  Total: 816 bytes")
    return size

def verify_file(filename):
    print(f"\n📄 Verifying: {filename}")
    
    with open(filename, 'rb') as f:
        data = f.read()
    
    size = len(data)
    print(f"  Size: {size} bytes")
    
    print(f"  First 64 bytes (hex):")
    for i in range(min(64, size)):
        if i % 16 == 0:
            print(f"    {i:04x}: ", end='')
        print(f"{data[i]:02x} ", end='')
        if (i + 1) % 16 == 0:
            print()
    print()
    
    if filename.endswith('_text.txt'):
        print(f"  First 10 lines:")
        lines = data.decode('utf-8').split('\n')[:10]
        for line in lines:
            print(f"    {line}")
    
    elif filename.endswith('_binary.bin'):
        print(f"  First 10 numbers (as uint32_t):")
        for i in range(min(10, size // 4)):
            num = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            print(f"    [{i}] = {num}")
    
    elif filename.endswith('_structured.bin'):
        magic = data[0:4]
        version = struct.unpack('<I', data[4:8])[0]
        num_entries = struct.unpack('<I', data[8:12])[0]
        
        print(f"  Header:")
        print(f"    Magic: {magic}")
        print(f"    Version: {version}")
        print(f"    Entries: {num_entries}")
        
        print(f"  First 5 entries:")
        for i in range(min(5, num_entries)):
            offset = 16 + i * 8
            index = struct.unpack('<I', data[offset:offset+4])[0]
            value = struct.unpack('<I', data[offset+4:offset+8])[0]
            print(f"    Entry[{index}]: value = {value}")

def main():
    print("=" * 60)
    print("Creating Test Files for I2C Slave Driver")
    print("=" * 60)
    
    print("\n1. Text file (numbers 1-100, one per line):")
    create_number_file_text('numbers_1_to_100_text.txt', 1, 100)
    
    print("\n2. Binary file (uint32_t array):")
    create_number_file_binary('numbers_1_to_100_binary.bin', 1, 100)
    
    print("\n3. Structured binary file:")
    create_structured_file('numbers_1_to_100_structured.bin')
    
    # 4. Pattern files
    print("\n4. Pattern files (for testing):")
    create_pattern_file('pattern_sequential.bin', 'sequential', 10)
    create_pattern_file('pattern_alternating.bin', 'alternating', 10)
    
    # Verify các file
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    verify_file('numbers_1_to_100_text.txt')
    verify_file('numbers_1_to_100_binary.bin')
    verify_file('numbers_1_to_100_structured.bin')
    
    print("\n" + "=" * 60)
    print("✓ All files created successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Load file into I2C slave driver:")
    print("   cat numbers_1_to_100_binary.bin > /sys/bus/i2c/devices/4-1064/slave-file")
    print("\n2. Run Raspberry Pi reader script:")
    print("   python3 i2c_reader.py")

if __name__ == '__main__':
    main()
