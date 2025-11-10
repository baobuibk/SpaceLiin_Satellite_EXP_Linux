#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

# ===============================
# CONFIGURATION
# ===============================
RAW_DECODER = "/home/root/tools/raw_imx93.py"
RAW_HEIGHT = 3840
RAW_WIDTH = 5120


def convert_raw(file_path, output_dir):
    """Convert a .raw file into two JPG images (low/high)."""
    if not os.path.exists(file_path):
        print(f"[Error] File does not exist: {file_path}")
        sys.exit(1)

    filename = os.path.basename(file_path)
    name_noext = os.path.splitext(filename)[0]

    base_output = os.path.join(output_dir, name_noext)
    output_low = base_output + "_low.jpg"
    output_high = base_output + "_high.jpg"

    print(f"[→] Decoding RAW: {file_path}")
    subprocess.run([
        "python3", RAW_DECODER,
        "-H", str(RAW_HEIGHT),
        "-W", str(RAW_WIDTH),
        file_path,
        "-o", base_output
    ], check=True)

    if os.path.exists(output_low) and os.path.exists(output_high):
        print(f"[OK] Created: {output_low}")
        print(f"[OK] Created: {output_high}")
    else:
        print("[Warning] Output files not found. Check RAW_DECODER or parameters!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a RAW file into two JPG images (low/high)"
    )
    parser.add_argument("raw_file", help="Path to the .raw file")
    parser.add_argument(
        "-o", "--output", default=".", help="Output directory (default: ./)"
    )
    args = parser.parse_args()

    convert_raw(args.raw_file, args.output)
