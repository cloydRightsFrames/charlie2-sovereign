#!/data/data/com.termux/files/usr/bin/bash
LOGF="$HOME/charlie2/logs/watchdog.log"
while true; do
  TS="[$(date '+%Y-%m-%d %H:%M:%S')]"
  if ! curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "$TS FastAPI DOWN - restarting" >> "$LOGF"
    pkill -f "python -m uvicorn main:app" 2>/dev/null; sleep 1
    cd ~/charlie2/api && nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 >> ~/charlie2/logs/api.log 2>&1 &
  fi
  if ! pgrep -x nginx > /dev/null 2>&1; then
    echo "$TS nginx DOWN - restarting" >> "$LOGF"; nginx 2>/dev/null &
  fi
  if ! pgrep -x redis-server > /dev/null 2>&1; then
    echo "$TS Redis DOWN - restarting" >> "$LOGF"
    redis-server ~/charlie2/redis.conf >> ~/charlie2/logs/redis.log 2>&1 &
  fi
  if ! curl -sf http://127.0.0.1:8002/cluster-status > /dev/null 2>&1; then
    echo "$TS Router DOWN - restarting" >> "$LOGF"
    pkill -f "inference_router.py" 2>/dev/null; sleep 1
    cd ~/charlie2 && nohup python inference_router.py >> ~/charlie2/logs/router.log 2>&1 &
  fi
  sleep 15
done
