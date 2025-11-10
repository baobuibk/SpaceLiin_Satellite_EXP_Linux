#!/usr/bin/env python3
from PIL import Image
import argparse
import os

SCALE = 1.0
QUALITY = 10

def compress_image(input_path, output_path, scale, quality, crop=False):
    img = Image.open(input_path).convert("RGB")
    w, h = img.size

    if crop:
        top_crop = int(h * 0.25)
        bottom_crop = h - int(h * 0.20)
        img = img.crop((0, top_crop, w, bottom_crop))
        print(f"[v] Cropped: removed 15% top/bottom → new size: {img.size[0]}x{img.size[1]}")

    if scale < 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size)
        print(f"[v] Resized: {w}x{h} → {new_size[0]}x{new_size[1]}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    img.save(
        output_path,
        format="JPEG",
        quality=quality,
        subsampling=2,  # 4:2:0 chroma subsampling
        optimize=True,
        progressive=True
    )

    old_size = os.path.getsize(input_path) / 1024
    new_size = os.path.getsize(output_path) / 1024
    print(f"[v] Saved: {output_path}")
    print(f"   Quality={quality}, Scale={scale}, Crop={crop}")
    print(f"   Size: {old_size:.1f} KB → {new_size:.1f} KB ({new_size/old_size*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress JPG with adjustable presets.")
    parser.add_argument("input", help="Input JPG file path")
    parser.add_argument("output", help="Output JPG file path")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--high", action="store_true", help="High quality: scale=1.0, quality=10")
    group.add_argument("--low", action="store_true", help="Low quality: scale=0.2, quality=20 + crop")
    args = parser.parse_args()

    scale = SCALE
    quality = QUALITY
    crop = False

    if args.high:
        scale = 1.0
        quality = 10
        crop = True  # kích hoạt crop cho high quality
    elif args.low:
        scale = 0.2
        quality = 20
        crop = True  # kích hoạt crop cho low quality

    compress_image(args.input, args.output, scale, quality, crop)
