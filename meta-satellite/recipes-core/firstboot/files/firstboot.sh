#!/bin/sh
FLAG=/etc/firstboot.done

if [ -f "$FLAG" ]; then
    exit 0
fi

echo "[FirstBoot] Starting"

for username in bee; do
    skel="/home/root/skel_${username}"
    HOME_DIR="/home/${username}"

    if id "$username" >/dev/null 2>&1; then
        echo "[FirstBoot] Installing $skel -> $HOME_DIR"
        install -d "$HOME_DIR"
        cp -a "$skel/." "$HOME_DIR/"
        chown -R "$username:$username" "$HOME_DIR"

        # Logic user
        case "$username" in
            bee)
                echo "[FirstBoot] Special setup for bee"
                ;;
            *)
                echo "[FirstBoot] No special setup for $username"
                ;;
        esac
    else
        echo "[FirstBoot] User $username not found; skipping"
    fi
done

sleep 1
timedatectl set-ntp false

# Set system time if /etc/custom-time exists
TIME_FILE="/etc/custom-time"
if [ -f "$TIME_FILE" ]; then
    TIME_STR=$(cat "$TIME_FILE")
    echo "[FirstBoot] Setting system time to: $TIME_STR"
    date -s "$TIME_STR"
    hwclock --systohc || true
else
    echo "[FirstBoot] No custom time file found at $TIME_FILE"
fi

# Edit resize bug
RESIZE_FILE="/etc/profile.d/resize.sh"
if [ -f "$RESIZE_FILE" ]; then
    echo "[FirstBoot] Patching $RESIZE_FILE"
    # Xóa toàn bộ dòng có từ "resize" (cũ)
    sed -i '/resize/d' "$RESIZE_FILE"
    # Thêm đoạn an toàn
    cat <<'EOF' >> "$RESIZE_FILE"
if [ -t 0 ] && command -v resize &>/dev/null; then
    timeout 0.1s resize >/dev/null 2>&1
fi
EOF
fi

# ---------------------------------------------------


touch "$FLAG"
echo "[FirstBoot] Done"
exit 0
