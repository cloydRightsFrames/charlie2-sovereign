#!/data/data/com.termux/files/usr/bin/bash
# Charlie 2.0 — Hardened Boot Script v2
# Runs automatically when Termux starts via Termux:Boot app
C2="$HOME/charlie2"
LOG="$C2/logs/boot.log"
ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo "[$(ts)] $1" >> "$LOG"; }

log "=== BOOT START ==="
sleep 8

# Activate swap
SWAPFILE="$HOME/charlie2_swap"
[ -f "$SWAPFILE" ] && {
  mkswap "$SWAPFILE" 2>/dev/null
  swapon "$SWAPFILE" 2>/dev/null \
    && log "Swap activated" \
    || log "Swap swapon not available"
}

# VM tuning
sysctl -w vm.swappiness=80 2>/dev/null
sysctl -w vm.vfs_cache_pressure=150 2>/dev/null
sysctl -w vm.overcommit_memory=1 2>/dev/null

# Redis on correct port
pkill -f redis-server 2>/dev/null; sleep 2
nohup redis-server \
  --port 6380 \
  --daemonize yes \
  --logfile "$C2/logs/redis.log" \
  --save "" \
  --maxmemory 128mb \
  --maxmemory-policy allkeys-lru 2>/dev/null
sleep 3; log "Redis started on :6380"

# nginx
nginx 2>/dev/null; log "nginx started"

# Tor
nohup tor -f "$C2/tor.conf" >> "$C2/logs/tor.log" 2>&1 &
sleep 3; log "Tor started"

# SSHD
sshd 2>/dev/null; log "SSHD started"

# Ollama
nohup ollama serve >> "$C2/logs/ollama.log" 2>&1 &
sleep 6; log "Ollama started"

# FastAPI — main sovereign stack
(builtin cd "$C2/api" && nohup python -m uvicorn main:app \
  --host 0.0.0.0 --port 8000 --workers 1 \
  >> "$C2/logs/api.log" 2>&1 &)
sleep 5

# FastAPI — AppCompat port
(builtin cd "$C2/api" && nohup python -m uvicorn main:app \
  --host 0.0.0.0 --port 8787 --workers 1 \
  >> "$C2/logs/api8787.log" 2>&1 &)

# Inference router
(builtin cd "$C2" && nohup python inference_router.py \
  >> "$C2/logs/router.log" 2>&1 &)
sleep 2; log "Inference router started"

# Sensor feed
nohup bash "$C2/sensor_feed.sh" >> "$C2/logs/sensor.log" 2>&1 &
log "Sensor feed started"

# Mesh daemon
nohup python "$C2/mesh/mesh_node.py" daemon \
  >> "$C2/logs/mesh.log" 2>&1 &
log "Mesh daemon started"

# Watchdog v2 — last, monitors everything else
sleep 5
nohup bash "$C2/watchdog.sh" >> "$C2/logs/watchdog.log" 2>&1 &
log "Watchdog v2 started"

# Log final state
sleep 8
RECORDS=$(python -c "import sqlite3,os; c=sqlite3.connect(os.path.expanduser('~/charlie2/charlie2.db')); print(c.execute('SELECT COUNT(*) FROM judicial_log').fetchone()[0])" 2>/dev/null || echo "?")
RAM=$(free -h 2>/dev/null | awk '/Mem/{print $3"/"$4}')
log "=== BOOT COMPLETE === records:$RECORDS ram:$RAM"
