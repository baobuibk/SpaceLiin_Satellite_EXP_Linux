#!/usr/bin/env python3
import os
import time
import shutil
import subprocess
import zipfile

# ===============================
# CONFIG
# ===============================
DATA_DIR = "/data"
TMP_DIR = os.path.join(DATA_DIR, ".a55_src/tmp")
ONESHOT_DIR = os.path.join(DATA_DIR, "Oneshot")
DAILY_HIGHRES_DIR = os.path.join(DATA_DIR, "Daily/HighRes")
DAILY_LOWRES_DIR = os.path.join(DATA_DIR, "Daily/LowRes")
ID_FILE = os.path.join(DATA_DIR, "count.txt")

# Autotest
AUTOTEST_DIR = os.path.join(DATA_DIR, "Autotest")
AUTOTEST_IMG_LOW_A = os.path.join(DATA_DIR, ".a55_src/Autotest_img_low_a")
AUTOTEST_IMG_LOW_B = os.path.join(DATA_DIR, ".a55_src/Autotest_img_low_b")
AUTOTEST_IMG_HIGH_A = os.path.join(DATA_DIR, ".a55_src/Autotest_img_high_a")
AUTOTEST_IMG_HIGH_B = os.path.join(DATA_DIR, ".a55_src/Autotest_img_high_b")
AUTOTEST_DATA = os.path.join(DATA_DIR, ".a55_src/Autotest_data")

RAW_DECODER = "/home/root/tools/raw_imx93.py"
JPG_COMPRESS = "/home/root/tools/jpg_compress.py"
RAW_HEIGHT = 3840
RAW_WIDTH = 5120

# ===============================
# UTILS
# ===============================
def get_next_id():
    if not os.path.exists(ID_FILE):
        with open(ID_FILE, "w") as f:
            f.write("0")
    with open(ID_FILE, "r+") as f:
        current = int(f.read().strip() or "0")
        new_id = current + 1
        f.seek(0)
        f.write(str(new_id))
        f.truncate()
    return new_id


def zip_files(file_list, dest_zip):
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in file_list:
            zipf.write(f, os.path.basename(f))


def process_oneshot(file_path):
    filename = os.path.basename(file_path)
    dest_path = os.path.join(ONESHOT_DIR, filename)
    shutil.move(file_path, dest_path)
    print(f"[Oneshot] Moved {filename} to {dest_path}")


def process_daily(file_path):
    filename = os.path.basename(file_path)
    parts = filename.split("_")
    if len(parts) < 3:
        print(f"[Pass] Filename wrong: {filename}")
        return

    camera = parts[1]
    epoch = parts[2].split(".")[0]
    next_id = get_next_id()
    id_str = f"{next_id:06d}"

    tmp_output_low = os.path.join(TMP_DIR, f"{camera}_{epoch}_low.jpg")
    tmp_output_high = os.path.join(TMP_DIR, f"{camera}_{epoch}_high.jpg")

    if camera.startswith("CAM"):
        base_output = os.path.join(TMP_DIR, f"{camera}_{epoch}")
        subprocess.run([
            "python3", RAW_DECODER,
            "-H", str(RAW_HEIGHT),
            "-W", str(RAW_WIDTH),
            file_path,
            "-o", base_output
        ], check=True)

        tmp_output_low = base_output + "_low.jpg"
        tmp_output_high = base_output + "_high.jpg"

        low_zip = os.path.join(DAILY_LOWRES_DIR, f"L{id_str}_{camera}_{epoch}.zip")
        high_zip = os.path.join(DAILY_HIGHRES_DIR, f"H{id_str}_{camera}_{epoch}.zip")
        zip_files([tmp_output_low], low_zip)
        zip_files([tmp_output_high], high_zip)

        os.remove(tmp_output_low)
        os.remove(tmp_output_high)
        os.remove(file_path)
        print(f"[Daily CAM] {filename} → {low_zip} / {high_zip}")
    else:
        low_zip = os.path.join(DAILY_LOWRES_DIR, f"L{id_str}_{camera}_{epoch}.zip")
        high_zip = os.path.join(DAILY_HIGHRES_DIR, f"H{id_str}_{camera}_{epoch}.zip")
        zip_files([file_path], low_zip)
        zip_files([file_path], high_zip)
        os.remove(file_path)
        print(f"[Daily Other] {filename} → {low_zip} / {high_zip}")


def process_autotest(file_path):
    filename = os.path.basename(file_path)
    basename, ext = os.path.splitext(filename)

    os.makedirs(AUTOTEST_IMG_LOW_A, exist_ok=True)
    os.makedirs(AUTOTEST_IMG_LOW_B, exist_ok=True)
    os.makedirs(AUTOTEST_IMG_HIGH_A, exist_ok=True)
    os.makedirs(AUTOTEST_IMG_HIGH_B, exist_ok=True)
    os.makedirs(AUTOTEST_DATA, exist_ok=True)

    # --- USB camera case ---
    if filename.startswith("oneshot_UCA0_") and ext.lower() == ".jpg":
        epoch = basename.split("_")[-1]

        # Kiểm tra có ảnh “before” chưa
        before_path = os.path.join(AUTOTEST_IMG_LOW_B, filename)
        after_path = os.path.join(AUTOTEST_IMG_LOW_A, filename)

        # Nếu chưa có “before” thì đây là before
        if not os.listdir(AUTOTEST_IMG_LOW_B):
            low_dest = before_path
            high_dest = os.path.join(AUTOTEST_IMG_HIGH_B, filename)
            print(f"[Autotest JPG] {filename} → before (B)")
        else:
            low_dest = after_path
            high_dest = os.path.join(AUTOTEST_IMG_HIGH_A, filename)
            print(f"[Autotest JPG] {filename} → after (A)")

        subprocess.run(["python3", JPG_COMPRESS, file_path, low_dest, "--low"], check=True)
        time.sleep(1)
        subprocess.run(["python3", JPG_COMPRESS, file_path, high_dest, "--high"], check=True)
        os.remove(file_path)

    # --- RAW camera cases ---
    elif filename.startswith("oneshot_CAM0_") and ext.lower() == ".raw":
        epoch = basename.split("_")[-1]
        print(f"[Autotest RAW] {filename} → before (B)")
        base_output = os.path.join(AUTOTEST_IMG_LOW_B, basename)
        subprocess.run([
            "python3", RAW_DECODER,
            "-H", str(RAW_HEIGHT),
            "-W", str(RAW_WIDTH),
            "-c",
            file_path,
            "-o", base_output
        ], check=True)

        # Sau khi chạy, sẽ có 2 file:
        #   <basename>_low.jpg
        #   <basename>_high.jpg
        # Di chuyển _high.jpg sang thư mục high_B
        low_path = base_output + "_low.jpg"
        high_path = base_output + "_high.jpg"
        shutil.move(high_path, os.path.join(AUTOTEST_IMG_HIGH_B, f"{basename}_high.jpg"))
        print(f"[Autotest RAW] {filename} → before (B)")

        os.remove(file_path)

    elif filename.startswith("oneshot_CAM2_") and ext.lower() == ".raw":
        epoch = basename.split("_")[-1]
        print(f"[Autotest RAW] {filename} → after (A)")
        base_output = os.path.join(AUTOTEST_IMG_LOW_A, basename)
        subprocess.run([
            "python3", RAW_DECODER,
            "-H", str(RAW_HEIGHT),
            "-W", str(RAW_WIDTH),
            "-c",
            file_path,
            "-o", base_output
        ], check=True)

        low_path = base_output + "_low.jpg"
        high_path = base_output + "_high.jpg"
        shutil.move(high_path, os.path.join(AUTOTEST_IMG_HIGH_A, f"{basename}_high.jpg"))
        print(f"[Autotest RAW] {filename} → after (A)")
        os.remove(file_path)

    # --- DATA (.dat) ---
    elif filename.startswith("oneshot_") and filename.endswith(".dat"):
        dest = os.path.join(AUTOTEST_DATA, filename)
        shutil.move(file_path, dest)
        print(f"[Autotest DATA] {filename} moved → Autotest_data")
    else:
        print(f"[Pass] Skip non-oneshot .dat file: {filename}")


def check_and_zip_autotest():
    """Kiểm tra đủ 5 loại nguyên liệu để tạo ZIP cho autotest"""
    os.makedirs(AUTOTEST_DIR, exist_ok=True)

    required_dirs = [
        AUTOTEST_IMG_LOW_A, AUTOTEST_IMG_LOW_B,
        AUTOTEST_IMG_HIGH_A, AUTOTEST_IMG_HIGH_B,
        AUTOTEST_DATA,
    ]

    # Kiểm tra tồn tại thư mục
    if not all(os.path.exists(d) for d in required_dirs):
        print("[Autotest] Some source folders missing → skip")
        return

    # Lấy danh sách file hiện có
    imgs_low_a = [os.path.join(AUTOTEST_IMG_LOW_A, f) for f in os.listdir(AUTOTEST_IMG_LOW_A) if os.path.isfile(os.path.join(AUTOTEST_IMG_LOW_A, f))]
    imgs_low_b = [os.path.join(AUTOTEST_IMG_LOW_B, f) for f in os.listdir(AUTOTEST_IMG_LOW_B) if os.path.isfile(os.path.join(AUTOTEST_IMG_LOW_B, f))]
    imgs_high_a = [os.path.join(AUTOTEST_IMG_HIGH_A, f) for f in os.listdir(AUTOTEST_IMG_HIGH_A) if os.path.isfile(os.path.join(AUTOTEST_IMG_HIGH_A, f))]
    imgs_high_b = [os.path.join(AUTOTEST_IMG_HIGH_B, f) for f in os.listdir(AUTOTEST_IMG_HIGH_B) if os.path.isfile(os.path.join(AUTOTEST_IMG_HIGH_B, f))]
    datas = [os.path.join(AUTOTEST_DATA, f) for f in os.listdir(AUTOTEST_DATA) if os.path.isfile(os.path.join(AUTOTEST_DATA, f))]

    # Chưa đủ 5 nhóm file thì thôi
    if not (imgs_low_a and imgs_low_b and imgs_high_a and imgs_high_b and datas):
        print("[Autotest] Waiting for all inputs (need 5 groups)")
        return

    # Di chuyển các ZIP cũ sang Oneshot thay vì xoá
    for f in os.listdir(AUTOTEST_DIR):
        src = os.path.join(AUTOTEST_DIR, f)
        dst = os.path.join(ONESHOT_DIR, f)
        try:
            shutil.move(src, dst)
            print(f"[Autotest] Moved old ZIP → Oneshot: {f}")
        except Exception as e:
            print(f"[Autotest] Warning: cannot move {f} → {e}")

    # Tạo ZIP mới (dựa vào epoch trong file data)
    for data in datas:
        epoch = os.path.basename(data).split("_")[-1].split(".")[0]
        low_zip = os.path.join(AUTOTEST_DIR, f"low_{epoch}.zip")
        high_zip = os.path.join(AUTOTEST_DIR, f"high_{epoch}.zip")

        try:
            zip_files(imgs_low_a + imgs_low_b + [data], low_zip)
            zip_files(imgs_high_a + imgs_high_b + [data], high_zip)
            print(f"[Autotest ZIP] Created low/high set for epoch {epoch}")
        except Exception as e:
            print(f"[Autotest] Error while zipping: {e}")

    # Xoá toàn bộ nguyên liệu sau khi zip thành công
    for folder in required_dirs:
        for f in os.listdir(folder):
            fpath = os.path.join(folder, f)
            try:
                os.remove(fpath)
            except Exception:
                pass
    print("[Autotest] Cleaned up all input files")


def main_loop():
    """Main watcher loop"""
    print("=== Watching tmp folder... ===")
    os.makedirs(ONESHOT_DIR, exist_ok=True)
    os.makedirs(DAILY_HIGHRES_DIR, exist_ok=True)
    os.makedirs(DAILY_LOWRES_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(AUTOTEST_DIR, exist_ok=True)

    # Đảm bảo thư mục autotest đủ cấu trúc
    for d in [
        AUTOTEST_IMG_LOW_A, AUTOTEST_IMG_LOW_B,
        AUTOTEST_IMG_HIGH_A, AUTOTEST_IMG_HIGH_B,
        AUTOTEST_DATA
    ]:
        try:
            for f in os.listdir(d):
                fpath = os.path.join(d, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
            print(f"[Init] Cleared old files in {d}")
        except Exception as e:
            print(f"[Init] Warning: cannot clear {d} → {e}")

    while True:
        try:
            files = [f for f in os.listdir(TMP_DIR) if os.path.isfile(os.path.join(TMP_DIR, f))]
            for f in files:
                fpath = os.path.join(TMP_DIR, f)

                # --- AUTOTEST ---
                # Gồm UCA0, CAM0, CAM2, hoặc file .dat
                if (
                    f.startswith("oneshot_UCA0_")
                    or f.startswith("oneshot_CAM0_")
                    or f.startswith("oneshot_CAM2_")
                    or (f.startswith("oneshot_") and f.endswith(".dat"))
                ):
                    process_autotest(fpath)

                # --- ONESHOT thông thường ---
                elif f.startswith("oneshot_"):
                    process_oneshot(fpath)

                # --- DAILY ---
                elif f.startswith("daily_"):
                    process_daily(fpath)

                else:
                    print(f"[Pass] {f}")

                time.sleep(1)

            # Sau khi xử lý xong tất cả file trong tmp, kiểm tra zip autotest
            check_and_zip_autotest()

        except Exception as e:
            print(f"[Error] {e}")

        time.sleep(3)

if __name__ == "__main__":
    main_loop()
