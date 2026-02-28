#!/bin/bash
# ============================================
# VieNeu-TTS + Whisper Startup Script
# ============================================
# Chạy: bash /root/start_all.sh
# Tắt:  bash /root/start_all.sh stop
# ============================================

export PATH="$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH=/root/VieNeu-TTS/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH

# Fix timezone
rm -rf /etc/localtime 2>/dev/null
ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime 2>/dev/null

# --- Stop all ---
if [ "$1" = "stop" ]; then
    echo "🛑 Stopping all services..."
    pkill -f "api_server.py" 2>/dev/null
    pkill -f "whisper-api/app.py" 2>/dev/null
    pkill -f "cloudflared" 2>/dev/null
    nginx -s stop 2>/dev/null
    echo "✅ All stopped."
    exit 0
fi

echo "🚀 Starting all services..."

# 1. Nginx
echo "  [1/4] Starting nginx..."
nginx -s stop 2>/dev/null
sleep 1
nginx
echo "  ✅ Nginx running on port 80"

# 2. Cloudflare Tunnel
echo "  [2/4] Starting Cloudflare Tunnel..."
cloudflared tunnel run --url http://localhost:80 vieneutts &>/var/log/cloudflared.log &
echo "  ✅ Tunnel running (log: /var/log/cloudflared.log)"

# 3. TTS API Server
echo "  [3/4] Starting TTS API..."
cd /root/VieNeu-TTS
uv run python apps/api_server.py &>/var/log/tts_api.log &
echo "  ✅ TTS API starting on port 8000 (log: /var/log/tts_api.log)"

# 4. Whisper STT
echo "  [4/4] Starting Whisper STT..."
cd /root/whisper-api
uv run python app.py &>/var/log/whisper.log &
echo "  ✅ Whisper starting on port 7861 (log: /var/log/whisper.log)"

echo ""
echo "============================================"
echo "  🎉 All services started!"
echo "  TTS API:  https://vieneutts.dukyai.com/api/tts"
echo "  Whisper:  https://whisper.dukyai.com"
echo "  Logs:     tail -f /var/log/tts_api.log"
echo "            tail -f /var/log/whisper.log"
echo "============================================"
