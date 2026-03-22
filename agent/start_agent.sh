#!/data/data/com.termux/files/usr/bin/bash
LOGF="$HOME/charlie2/logs/agent.log"
echo "[$(date)] Agent starting" >> "$LOGF"
python "$HOME/charlie2/agent/coding_agent.py" watch --push \
  >> "$LOGF" 2>&1
