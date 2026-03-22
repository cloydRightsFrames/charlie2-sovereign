#!/data/data/com.termux/files/usr/bin/bash
WATCH="$HOME/charlie2/api"
LAST=""
while true; do
  CURRENT=$(find "$WATCH" -name "*.py" -newer "$HOME/charlie2/logs/sync.log" 2>/dev/null | wc -l)
  if [ "$CURRENT" != "$LAST" ] && [ "$CURRENT" -gt "0" ]; then
    LAST="$CURRENT"; bash ~/charlie2/sync_to_pc.sh
  fi
  sleep 30
done
