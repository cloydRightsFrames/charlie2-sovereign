#!/data/data/com.termux/files/usr/bin/bash
PC=""
echo "[$(date)] Syncing to $PC..." >> "$HOME/charlie2/logs/sync.log"
rsync -avz --delete --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.db' --exclude='llama.cpp/build' --exclude='whisper.cpp/build' $HOME/charlie2/ charlie@${PC}:/Users/charlie/charlie2/ >> "$HOME/charlie2/logs/sync.log" 2>&1
echo "[$(date)] Sync done" >> "$HOME/charlie2/logs/sync.log"
