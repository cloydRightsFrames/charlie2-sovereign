#!/data/data/com.termux/files/usr/bin/bash
export OLLAMA_HOST=0.0.0.0:11434
pkill -x ollama 2>/dev/null; sleep 1
nohup ollama serve >> ~/charlie2/logs/ollama.log 2>&1 &
sleep 6
ollama list 2>/dev/null | grep -q "deepseek-coder" || \
  ollama pull deepseek-coder:1.3b >> ~/charlie2/logs/ollama.log 2>&1 &
echo "[$(date)] Ollama started" >> ~/charlie2/logs/ollama.log
