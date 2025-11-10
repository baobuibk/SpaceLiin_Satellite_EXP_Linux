#!/usr/bin/env python3
"""
python_exec.py : unified handler for Table7 (0x0700–0x0706)

Usage examples:
  python3 python_exec.py 0701
  python3 python_exec.py 0702 512
  python3 python_exec.py 0703 /path/to/file
  python3 python_exec.py 0705 3
"""

import sys, os, math, struct, shutil, glob, zlib, subprocess, sqlite3, re, datetime

BASE   = "/data/.a55_src"
TMPDIR = f"{BASE}/tmp_part"
LISTF  = f"{BASE}/list_files.txt"
DB     = f"{BASE}/bee_params.db"

def ensure_dirs():
    os.makedirs(BASE, exist_ok=True)
    os.makedirs(TMPDIR, exist_ok=True)

def crc32_iso(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

def db_conn():
    os.makedirs(BASE, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS file_state (k TEXT PRIMARY KEY, v TEXT)")
    return con

def db_set(k, v):
    con = db_conn(); con.execute("REPLACE INTO file_state VALUES (?,?)",(k,v)); con.commit(); con.close()
def db_get(k, d=None):
    con = db_conn(); cur = con.cursor(); cur.execute("SELECT v FROM file_state WHERE k=?",(k,))
    r = cur.fetchone(); con.close(); return r[0] if r else d

def _parse_epoch_from_name(name: str):
    """Tìm chuỗi epoch 10 chữ số trong tên file, trả về set[int]."""
    epochs = set()
    for m in re.findall(r"(\d{10})", name):
        try:
            epochs.add(int(m))
        except ValueError:
            pass
    return epochs

def cmd_0701():
    """create list_files.txt"""
    try:
        with open(LISTF, "wb") as fo:
            subprocess.run([
                "tree", "-ah", "--noreport", "/data",
                "-I", ".*|.a55*|*.log|*.log.[0-9]*|*.err|*.err.[0-9]*"
            ], stdout=fo, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        with open(LISTF, "wb") as fo:
            for root, dirs, files in os.walk("/data"):
                # Bỏ qua các file hoặc thư mục theo cùng logic
                dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith(".a55")]
                for n in dirs + files:
                    if (n.startswith(".") or 
                        n.startswith(".a55") or 
                        n.endswith(".log") or 
                        ".log." in n or 
                        n.endswith(".err") or 
                        ".err." in n):
                        continue
                    fo.write((os.path.join(root, n) + "\n").encode())
    size = os.path.getsize(LISTF)
    sys.stdout.buffer.write(size.to_bytes(4, "big"))

def cmd_0702(chunk:int):
    """split list_files.txt into parts"""
    if not os.path.exists(LISTF):
        sys.stdout.buffer.write((0).to_bytes(8,"big")); return
    shutil.rmtree(TMPDIR,ignore_errors=True); os.makedirs(TMPDIR,exist_ok=True)
    fsize=os.path.getsize(LISTF); npart=(fsize+chunk-1)//chunk
    with open(LISTF,"rb") as f:
        for i in range(npart):
            open(f"{TMPDIR}/list_files.txt_part_{i}","wb").write(f.read(chunk))
    sys.stdout.buffer.write(fsize.to_bytes(4,"big")+npart.to_bytes(4,"big"))

def cmd_0703(rel_path: str, chunk: int):
    """load_file_by_name: nhận đường dẫn tương đối từ /data/"""
    fname = os.path.join("/data", rel_path)
    if not os.path.isfile(fname):
        sys.stdout.buffer.write((0).to_bytes(8,"big"))
        return
    shutil.rmtree(TMPDIR, ignore_errors=True)
    os.makedirs(TMPDIR, exist_ok=True)

    db_set("current_file", fname)
    db_set("current_index", "0")

    fsize = os.path.getsize(fname)
    npart = (fsize + chunk - 1) // chunk
    base = os.path.basename(fname)
    with open(fname, "rb") as f:
        for i in range(npart):
            open(f"{TMPDIR}/{base}_part_{i}", "wb").write(f.read(chunk))
    sys.stdout.buffer.write(fsize.to_bytes(4,"big") + npart.to_bytes(4,"big"))

def cmd_0704(file_id: int, chunk: int):
    """load_next_file: chỉ load LowRes file theo ID"""
    lowres_dir = "/data/Daily/LowRes"
    prefix = f"L{file_id:06d}_"
    found = None
    for name in sorted(os.listdir(lowres_dir)):
        if name.startswith(prefix) and name.endswith(".zip"):
            found = os.path.join(lowres_dir, name)
            break
    if not found:
        sys.exit(0)

    shutil.rmtree(TMPDIR, ignore_errors=True)
    os.makedirs(TMPDIR, exist_ok=True)

    fsize = os.path.getsize(found)
    npart = (fsize + chunk - 1) // chunk
    base = os.path.basename(found)
    with open(found, "rb") as f:
        for i in range(npart):
            open(f"{TMPDIR}/{base}_part_{i}", "wb").write(f.read(chunk))

    db_set("current_file", found)
    sys.stdout.buffer.write(fsize.to_bytes(4,"big") + npart.to_bytes(4,"big") + base.encode())

def cmd_0705(part_no:int):
    """load_part: only write to I2C EEPROM and return header info (no data)"""
    import subprocess, stat

    parts = sorted(glob.glob(f"{TMPDIR}/*_part_*"))
    if part_no < 0 or part_no >= len(parts):
        sys.exit(2)

    file_path = parts[part_no]
    # Write part directly to I2C EEPROM device (cat -> exprom-file)
    EXPROM = "/sys/bus/i2c/devices/4-1064/exprom-file"
    cmd = f"cat \"{file_path}\" > {EXPROM}"
    ret = os.system(cmd)
    if ret != 0:
        print(f"[0705] Warning: system() cat failed ({ret})", file=sys.stderr)

    # Read file to calculate CRC-32 (ISO-HDLC)
    with open(file_path, "rb") as f:
        data = f.read()
    crc = crc32_iso(data)

    psize = len(data)

    # Response frame (no data): partNo(4) + psize(4) + crc32(4)
    out = (
        part_no.to_bytes(4, "big")
        + psize.to_bytes(4, "big")
        + crc.to_bytes(4, "big")
    )
    sys.stdout.buffer.write(out)
    print(
        f"[0705] Part={part_no}, Size={psize}, CRC=0x{crc:08X}, written to exprom-file",
        file=sys.stderr,
    )

def cmd_0706(rel_path: str):
    """delete file theo đường dẫn tương đối từ /data/"""
    fname = os.path.join("/data", rel_path)
    rc = 0
    try:
        if os.path.isfile(fname):
            os.remove(fname)
        base = os.path.basename(fname)
        for p in glob.glob(f"{TMPDIR}/{base}_part_*"):
            os.remove(p)
    except Exception:
        rc = 0xFFFFFFFF
    sys.stdout.buffer.write(rc.to_bytes(4,"big"))

def cmd_0707(yymmdd: str):
    """
    Xoá các file trong /data/Daily/{HighRes,LowRes} có epoch (10 digits) nằm trong ngày YYMMDD (UTC).
    Output: 4 byte BE = count đã xoá.
    """
    if not (isinstance(yymmdd, str) and len(yymmdd) == 6 and yymmdd.isdigit()):
        sys.exit(2)

    yy = int(yymmdd[0:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])
    year = 2000 + yy

    try:
        dt0 = datetime.datetime(year, mm, dd, 0, 0, 0, tzinfo=datetime.timezone.utc)
    except ValueError:
        sys.exit(2)
    start_epoch = int(dt0.timestamp())
    end_epoch   = start_epoch + 86400

    roots = ["/data/Daily/HighRes", "/data/Daily/LowRes"]

    deleted = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            epochs = _parse_epoch_from_name(name)
            # Bỏ qua file không có epoch, hoặc epoch = 0
            if not epochs:
                continue
            if any(start_epoch <= e < end_epoch for e in epochs):
                fpath = os.path.join(root, name)
                try:
                    os.remove(fpath); deleted += 1
                except Exception:
                    pass
    sys.stdout.buffer.write(deleted.to_bytes(4,"big"))

def cmd_0710():
    """
    Liệt kê thông tin file trong /data/Autotest:
    Trả về:
    2 byte echo (0x07,0x10)
    low:  size(4) epoch(4) nPart(4) crc(3)
    high: size(4) epoch(4) nPart(4) crc(3)
    """
    import struct, zlib, os, math
    root = "/data/Autotest"
    out = bytearray()

    def info(path):
        if not path or not os.path.isfile(path):
            return b"\xFF" * (4 + 4 + 4 + 4)
        size = os.path.getsize(path)
        match = re.findall(r"(\d{10})", os.path.basename(path))
        epoch = int(match[0]) if match else 0
        n_part = (size + 199) // 200
        with open(path, "rb") as f:
            data = f.read()
        crc = zlib.crc32(data) & 0xFFFFFFFF
        return struct.pack(">III", size, epoch, n_part) + crc.to_bytes(4, "big")


    low_file = None
    high_file = None
    for name in os.listdir(root):
        if name.startswith("low_") and name.endswith(".zip"):
            low_file = os.path.join(root, name)
        elif name.startswith("high_") and name.endswith(".zip"):
            high_file = os.path.join(root, name)
    out += info(low_file) + info(high_file)
    sys.stdout.buffer.write(out)


def cmd_0711(part_no: int):
    """Lấy dữ liệu từ part cụ thể của file low_<epoch>.zip"""
    _get_autotest_part("low", part_no)

def cmd_0712(part_no: int):
    """Lấy dữ liệu từ part cụ thể của file high_<epoch>.zip"""
    _get_autotest_part("high", part_no)

def _get_autotest_part(kind: str, part_no: int):
    import struct, zlib, os, re, sys

    path = None
    for name in os.listdir("/data/Autotest"):
        if name.startswith(f"{kind}_") and name.endswith(".zip"):
            path = os.path.join("/data/Autotest", name)
            break

    if not path:
        # epoch(4) + part_no(4) + psize(4) + data(200) + crc(4)
        sys.stdout.buffer.write(b"\xFF" * (4 + 4 + 4 + 200 + 4))
        return

    size = os.path.getsize(path)
    match = re.findall(r"(\d{10})", os.path.basename(path))
    epoch = int(match[0]) if match else 0
    n_part = (size + 199) // 200

    if part_no >= n_part:
        sys.exit(2)

    with open(path, "rb") as f:
        f.seek(part_no * 200)
        data = f.read(200)

    psize = len(data)
    crc = zlib.crc32(data) & 0xFFFFFFFF  # đủ 4 byte CRC

    # Không cần 0x07, 0x11, 0x12 nữa
    out = bytearray()
    out += struct.pack(">I", epoch)
    out += struct.pack(">I", part_no)
    out += struct.pack(">I", psize)
    out += data
    out += crc.to_bytes(4, "big")  # đủ 4 byte

    sys.stdout.buffer.write(out)


def main():
    ensure_dirs()
    if len(sys.argv) < 2:
        sys.exit(1)
    addr = sys.argv[1]
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None
    arg3 = sys.argv[3] if len(sys.argv) > 3 else None

    if addr == "0701":
        cmd_0701()
    elif addr == "0702":
        cmd_0702(int(arg2) if arg2 else 512)
    elif addr == "0703":
        if not arg2:
            sys.exit(2)
        chunk = int(arg3) if arg3 else 512
        cmd_0703(arg2, chunk)
    elif addr == "0704":
        if not arg2:
            sys.exit(2)
        file_id = int(arg2)
        chunk = int(arg3) if arg3 else 512
        cmd_0704(file_id, chunk)
    elif addr == "0705":
        cmd_0705(int(arg2) if arg2 else 0)
    elif addr == "0706":
        if not arg2:
            sys.exit(2)
        cmd_0706(arg2)
    elif addr == "0707":
        if not arg2:
            sys.exit(2)
        cmd_0707(arg2)
    elif addr == "0710":
        cmd_0710()
    elif addr == "0711":
        cmd_0711(int(arg2) if arg2 else 0)
    elif addr == "0712":
        cmd_0712(int(arg2) if arg2 else 0)
    else:
        sys.exit(99)


if __name__=="__main__":
    main()