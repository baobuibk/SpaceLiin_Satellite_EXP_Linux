#!/bin/sh
# ============================================================
# Supervisor setup script for PAY-EXP Satellite system
# ============================================================

CONF_DIR="/etc/supervisor/conf.d"
LOG_DIR="/data/Oneshot"
SUP_CONF="/etc/supervisor/supervisord.conf"

echo "[INFO] === Supervisor setup starting ==="

# 1️⃣ Ensure folders exist
mkdir -p "$CONF_DIR" "$LOG_DIR"
chmod 755 "$LOG_DIR"

# 2️⃣ Check supervisord binary
if ! command -v supervisord >/dev/null 2>&1; then
    echo "[ERROR] supervisord not found. Please install supervisor first."
    exit 1
fi

# 3️⃣ Create main supervisord.conf if missing
if [ ! -f "$SUP_CONF" ]; then
    echo "[INFO] Creating default $SUP_CONF"
    echo_supervisord_conf > "$SUP_CONF"
    sed -i 's@;files = .*@files = /etc/supervisor/conf.d/*.conf@g' "$SUP_CONF"
fi

# 4️⃣ Create configuration files
echo "[INFO] Generating Supervisor program configs..."

# ---- step1_exp_server.conf ----
cat > "$CONF_DIR/step1_exp_server.conf" <<'EOF'
[program:exp_server]
command=/home/root/.a55_src/00_src/libcsp/00_Dev16/DevBuild/exp_server
autostart=true
autorestart=true
startsecs=5
priority=10
stdout_logfile=/data/Oneshot/exp_server.log
stderr_logfile=/data/Oneshot/exp_server.err
stdout_logfile_maxbytes=256KB
stderr_logfile_maxbytes=256KB
EOF

# ---- step2_file_watcher.conf ----
cat > "$CONF_DIR/step2_file_watcher.conf" <<'EOF'
[program:file_watcher]
command=python3 /home/root/tools/file_watcher.py
autostart=true
autorestart=true
startsecs=3
priority=20
stdout_logfile=/data/Oneshot/file_watcher.log
stderr_logfile=/data/Oneshot/file_watcher.err
stdout_logfile_maxbytes=256KB
stderr_logfile_maxbytes=256KB
EOF

# ---- step3_m33_reload.conf ----
cat > "$CONF_DIR/step3_m33_reload.conf" <<'EOF'
[program:m33_reload]
command=/bin/sh -c "sleep 5; for i in 1 2 3; do bash /home/root/tools/stop_m33.sh; sleep 1; done; bash /home/root/tools/run_m33.sh /home/bee/payexp_m33.elf"
autostart=true
autorestart=false
startsecs=2
priority=30
stdout_logfile=/data/Oneshot/m33_reload.log
stderr_logfile=/data/Oneshot/m33_reload.err
stdout_logfile_maxbytes=256KB
stderr_logfile_maxbytes=256KB
EOF

# ---- step4_modprobe.conf ----
cat > "$CONF_DIR/step4_modprobe.conf" <<'EOF'
[program:modprobe_imx_rpmsg]
command=/bin/sh -c "sleep 8; modprobe imx_rpmsg_hybrid"
autostart=true
autorestart=false
priority=40
stdout_logfile=/data/Oneshot/modprobe.log
stderr_logfile=/data/Oneshot/modprobe.err
stdout_logfile_maxbytes=128KB
stderr_logfile_maxbytes=128KB
EOF

# ---- step5_rpmsg_daemons.conf ----
cat > "$CONF_DIR/step5_rpmsg_daemons.conf" <<'EOF'
[program:rpmsg_daemon]
command=/bin/sh -c "sleep 10; python3 /home/root/tools/rpmsg_daemon.py"
autostart=true
autorestart=true
startsecs=3
priority=50
stdout_logfile=/data/Oneshot/rpmsg_daemon.log
stderr_logfile=/data/Oneshot/rpmsg_daemon.err
stdout_logfile_maxbytes=256KB
stderr_logfile_maxbytes=256KB

[program:file_daemon]
command=/bin/sh -c "sleep 11; python3 /home/root/tools/file_daemon.py"
autostart=true
autorestart=true
startsecs=3
priority=51
stdout_logfile=/data/Oneshot/file_daemon.log
stderr_logfile=/data/Oneshot/file_daemon.err
stdout_logfile_maxbytes=256KB
stderr_logfile_maxbytes=256KB
EOF

# 5️⃣ Reload supervisor configs
echo "[INFO] Reloading supervisor configuration..."
supervisorctl reread
supervisorctl update

# 6️⃣ Show status
echo "[INFO] Current supervisor process status:"
supervisorctl status

echo "[INFO] === Supervisor setup completed successfully ==="
