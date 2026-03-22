#!/data/data/com.termux/files/usr/bin/bash
FEED="$HOME/charlie2/sensor_context.json"
LOGF="$HOME/charlie2/logs/sensor.log"
echo "[$(date)] Sensor feed started" >> "$LOGF"
while true; do
  BATTERY=$(termux-battery-status 2>/dev/null || echo '{"status":"unknown"}')
  WIFI=$(termux-wifi-connectioninfo 2>/dev/null || echo '{"ssid":"unknown"}')
  MEM=$(free -h 2>/dev/null | awk 'NR==2{printf "{\"used\":\"%s\",\"total\":\"%s\"}",$3,$2}')
  LOAD=$(uptime | awk -F'load average:' '{print $2}' | xargs)
  printf '{\n  "timestamp": "%s",\n  "battery": %s,\n  "wifi": %s,\n  "memory": %s,\n  "load_average": "%s",\n  "uptime": "%s",\n  "processes": %s\n}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BATTERY" "$WIFI" "$MEM" "$LOAD" \
    "$(uptime -p 2>/dev/null)" "$(ps aux 2>/dev/null | wc -l)" > "$FEED"
  sleep 30
done
