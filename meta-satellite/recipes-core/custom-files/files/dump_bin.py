#!/usr/bin/env python3

import sys
import os

def dump_bin_file(filepath):
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    with open(filepath, 'rb') as f:
        data = f.read()

    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]

        print(f"0x{offset:08X}:", end=' ')

        hex_part = ' '.join(f"{b:02X}" for b in chunk)
        print(hex_part.ljust(16 * 3 - 1), end='  ')

        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"|{ascii_part}|")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename.bin>")
        sys.exit(1)

    dump_bin_file(sys.argv[1])
