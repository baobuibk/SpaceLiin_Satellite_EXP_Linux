#!/usr/bin/env python3
import sys
import argparse
import os
import numpy as np
from PIL import Image
from raw_decoder import Raw10PaddedImage
import gc, time

# ===== Config dễ chỉnh ở đây =====
CROP_TOP = 0.0
CROP_BOTTOM = 0.5
CROP_LEFT = 0.0
CROP_RIGHT = 0.5
# =================================

def main():
    parser = argparse.ArgumentParser(description='Convert raw10p image to dual JPEGs (IMX93 minimal).')
    parser.add_argument('-H', dest='height', type=int, required=True)
    parser.add_argument('-W', dest='width', type=int, required=True)
    parser.add_argument('-s', dest='offset', type=int, default=0)
    parser.add_argument('-o', dest='outfile', metavar='FILE', required=True,
                        help='Output base path (without _low/_high suffix)')
    parser.add_argument('-b', dest='bayer', choices=['rggb', 'bggr', 'grbg', 'gbrg'], default='grbg')
    parser.add_argument('-c', dest='crop', action='store_true',
                        help='Enable cropping for low-quality image')
    parser.add_argument('infile', metavar='InputRawFile', help='Input raw10p file')
    args = parser.parse_args()

    base_out = os.path.splitext(args.outfile)[0]
    out_low = base_out + "_low.jpg"
    out_high = base_out + "_high.jpg"

    # Load RAW10 padded (10-bit in 16-bit)
    raw_img = Raw10PaddedImage(args.infile, args.width, args.height, args.offset, args.bayer)
    raw_img.load()
    rgb = raw_img.getRGB()
    if rgb.dtype != np.float32:
        rgb = rgb.astype(np.float32, copy=False)

    # Clip and convert to 8-bit
    np.clip(rgb, 0.0, 1.0, out=rgb)
    rgb8 = (rgb * 255).astype(np.uint8)
    del rgb
    gc.collect()

    h, w, _ = rgb8.shape
    img = Image.fromarray(rgb8, mode='RGB')
    del rgb8
    gc.collect()

    # --- Save high-quality full image ---
    img.save(out_high,
             format='JPEG',
             quality=90,
             subsampling=0,
             optimize=False)
    print(f"[v] Saved high quality: {out_high}")

    # --- Create low-quality version ---
    if args.crop:
        left = int(w * CROP_LEFT)
        right = int(w * (1.0 - CROP_RIGHT))
        top = int(h * CROP_TOP)
        bottom = int(h * (1.0 - CROP_BOTTOM))
        img_low = img.crop((left, top, right, bottom))
        print(f"[v] Cropped low image: top={CROP_TOP}, bottom={CROP_BOTTOM}, left={CROP_LEFT}, right={CROP_RIGHT}")
    else:
        img_low = img.copy()  # không crop

    img_low = img_low.resize((img_low.width // 4, img_low.height // 4))
    img_low.save(out_low, format='JPEG', quality=60, subsampling=2, optimize=True)
    print(f"[v] Saved low quality: {out_low}")

    del img, img_low, raw_img
    gc.collect()
    time.sleep(0.3)
    print("[v] Done: both low/high generated")

if __name__ == "__main__":
    main()
