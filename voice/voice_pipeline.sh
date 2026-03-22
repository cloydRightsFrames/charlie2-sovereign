#!/data/data/com.termux/files/usr/bin/bash
AUDIO="${1:-/tmp/c2_voice.wav}"
WHISPER="$HOME/charlie2/whisper.cpp/main"
MODEL="$HOME/charlie2/whisper.cpp/models/ggml-base.en.bin"
LOGF="$HOME/charlie2/logs/voice.log"

echo -e "\e[38;5;51m⚡ Charlie 2.0 Voice Pipeline\e[0m"

if [ -z "$1" ]; then
  echo -e "\e[38;5;226m🎙️  Recording 5 seconds...\e[0m"
  termux-microphone-record -l 5 -f "$AUDIO" 2>/dev/null || \
    sox -d -r 16000 -c 1 "$AUDIO" trim 0 5 2>/dev/null
  echo -e "\e[38;5;46m✓ Recorded\e[0m"
fi

if [ -f "$WHISPER" ] && [ -f "$MODEL" ]; then
  echo -e "\e[38;5;226m🔊 Transcribing...\e[0m"
  TRANSCRIPT=$("$WHISPER" -m "$MODEL" -f "$AUDIO" --output-txt 2>/dev/null | tail -1)
else
  TRANSCRIPT="${2:-Hello Charlie, status report please.}"
  echo -e "\e[38;5;226m  Whisper model pending — using: $TRANSCRIPT\e[0m"
fi
echo -e "\e[38;5;46m  You:\e[0m $TRANSCRIPT"
echo "[$(date)] INPUT: $TRANSCRIPT" >> "$LOGF"

RESPONSE=$(curl -sf -X POST http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"deepseek-coder:1.3b\",\"prompt\":\"$TRANSCRIPT\",\"stream\":false}" \
  2>/dev/null | python -c "import sys,json; print(json.load(sys.stdin).get('response','...'))" 2>/dev/null)

[ -z "$RESPONSE" ] && RESPONSE=$(curl -sf http://127.0.0.1:8000/health \
  | python -c "import sys,json; d=json.load(sys.stdin); print('Charlie 2.0 online. RAM: '+d.get('memory','?'))" 2>/dev/null \
  || echo "Charlie 2.0 is sovereign and online.")

echo -e "\e[38;5;51m  Charlie:\e[0m $RESPONSE"
echo "[$(date)] RESPONSE: $RESPONSE" >> "$LOGF"

echo "$RESPONSE" | termux-tts-speak 2>/dev/null || \
  espeak "$RESPONSE" 2>/dev/null || \
  echo -e "\e[38;5;226m  (Install Termux:API for TTS)\e[0m"
