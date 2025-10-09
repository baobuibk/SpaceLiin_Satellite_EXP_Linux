#!/bin/sh
FLAG=/etc/firstboot.done

if [ -f "$FLAG" ]; then
    exit 0
fi

echo "[FirstBoot] Starting"

for username in esat93; do
    skel="/home/root/skel_${username}"
    HOME_DIR="/home/${username}"

    if id "$username" >/dev/null 2>&1; then
        echo "[FirstBoot] Installing $skel -> $HOME_DIR"
        install -d "$HOME_DIR"
        cp -a "$skel/." "$HOME_DIR/"
        chown -R "$username:$username" "$HOME_DIR"

        # Logic user
        case "$username" in
            esat93)
                echo "[FirstBoot] Special setup for esat93"
                ;;
            *)
                echo "[FirstBoot] No special setup for $username"
                ;;
        esac
    else
        echo "[FirstBoot] User $username not found; skipping"
    fi
done

touch "$FLAG"
echo "[FirstBoot] Done"
exit 0
