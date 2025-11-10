#!/bin/sh
set -eu

# Flag read-only rootfs:
FLAG_DATA="/data/.firstboot_data_done"
FLAG_VOL="/var/volatile/.firstboot_data_done"

[ -f "$FLAG_DATA" ] || [ -f "$FLAG_VOL" ] && exit 0

echo "[grow-fs] Detecting root device..."
rootdev="$(findmnt -n -o SOURCE /)"          # /dev/mmcblk1p2
disk="${rootdev%p*}"                          # /dev/mmcblk1
p3="${disk}p3"

echo "[grow-fs] rootdev=$rootdev disk=$disk p3=$p3"

if ! [ -b "$p3" ]; then
  echo "[grow-fs] Creating p3..."
  echo ",,L" | sfdisk --append --no-reread "$disk" || true
  sync
  echo "[grow-fs] Partition table updated. Kernel will reload on next boot."
  touch "$FLAG_VOL"
  reboot
  exit 0
fi

for i in $(seq 1 12); do
  [ -b "$p3" ] && break
  echo "[grow-fs] Waiting for $p3..."
  sleep 1
done
[ -b "$p3" ] || { echo "[grow-fs] ERROR: $p3 not found"; exit 1; }

if ! blkid "$p3" | grep -q 'TYPE="ext4"'; then
  echo "[grow-fs] Formatting $p3 (ext4, LABEL=DATA)..."
  mkfs.ext4 -F -L DATA "$p3"
fi

mkdir -p /data

if ! grep -q "LABEL=DATA" /etc/fstab 2>/dev/null; then
  echo "LABEL=DATA  /data  ext4  defaults,noatime,commit=30  0  2" >> /etc/fstab
fi

if ! mountpoint -q /data; then
  mount "$p3" /data || mount LABEL=DATA /data || true
fi

echo "[grow-fs] Running e2fsck/resize2fs..."
e2fsck -pf "$p3" || true
resize2fs "$p3" || true

mkdir -p /data/{.db,.cache}
chmod 755 /data

touch "$FLAG_DATA" 2>/dev/null || touch "$FLAG_VOL"

echo "[grow-fs] Done."
exit 0
