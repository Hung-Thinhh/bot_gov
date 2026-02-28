#!/bin/bash
# ============================================
# VieNeu-TTS + Whisper Startup Script
# ============================================
# Dành cho: chiasegpu.vn container restart
# Chạy: bash /root/start_all.sh
# Tắt:  bash /root/start_all.sh stop
# ============================================

export PATH="$HOME/.local/bin:$PATH"
# Add CUDA libraries from venv (cho cả TTS và Whisper)
export LD_LIBRARY_PATH=/root/VieNeu-TTS/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH

# Fix timezone
rm -rf /etc/localtime 2>/dev/null
ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime 2>/dev/null

# --- Stop all ---
if [ "$1" = "stop" ]; then
    echo "🛑 Stopping all services..."
    pkill -9 -f "api_server.py" 2>/dev/null
    pkill -9 -f "whisper-api/app.py" 2>/dev/null
    pkill -9 -f "cloudflared" 2>/dev/null
    nginx -s stop 2>/dev/null
    sleep 2
    echo "✅ All stopped."
    exit 0
fi

echo "🚀 Starting all services..."
echo "   Platform: chiasegpu.vn GPU Container"
echo ""

# Kill các process cũ nếu còn sót (phòng khi container bị pause/resume)
pkill -9 -f "api_server.py" 2>/dev/null
pkill -9 -f "whisper-api/app.py" 2>/dev/null
pkill -9 -f "cloudflared" 2>/dev/null
nginx -s stop 2>/dev/null
sleep 2

# 1. Nginx
echo "  [1/4] Starting nginx..."
nginx
echo "  ✅ Nginx running on port 80"

# 2. Cloudflare Tunnel
echo "  [2/4] Starting Cloudflare Tunnel..."
if [ -f /root/.cloudflared/config.yml ]; then
    # Run with config file (đã cấu hình đúng với hostname)
    nohup cloudflared tunnel --config /root/.cloudflared/config.yml run > /var/log/cloudflared.log 2>&1 &
    echo "  ✅ Tunnel starting with config..."
else
    echo "  ❌ ERROR: /root/.cloudflared/config.yml not found!"
    echo "     Run: cloudflared tunnel login"
    exit 1
fi

# 3. TTS API Server
echo "  [3/4] Starting TTS API (Model: VieNeu-TTS 0.5B)..."
cd /root/VieNeu-TTS
# Model: pnnbao-ump/VieNeu-TTS (0.5B - Maximum Quality)
nohup uv run python apps/api_server.py > /var/log/tts_api.log 2>&1 &
echo "  ✅ TTS API starting on port 8000"

# 4. Whisper STT
echo "  [4/4] Starting Whisper STT..."
cd /root/whisper-api
nohup uv run python app.py > /var/log/whisper.log 2>&1 &
echo "  ✅ Whisper starting on port 7861"

echo ""
echo "⏳ Waiting for services to be ready... (15s)"
sleep 15

# Health check
echo ""
echo "🔍 Health Check:"
TTS_STATUS=$(curl -s http://localhost:8000/api/health 2>/dev/null | grep -o '"status":"ok"' || echo "FAIL")
WHISPER_STATUS=$(curl -s http://localhost:7861/api/health 2>/dev/null | grep -o '"status":"ok"' || echo "FAIL")

if [ "$TTS_STATUS" = '"status":"ok"' ]; then
    echo "  ✅ TTS API: OK (Port 8000)"
else
    echo "  ⚠️  TTS API: Starting... (check: tail -f /var/log/tts_api.log)"
fi

if [ "$WHISPER_STATUS" = '"status":"ok"' ]; then
    echo "  ✅ Whisper API: OK (Port 7861)"
else
    echo "  ⚠️  Whisper API: Starting... (check: tail -f /var/log/whisper.log)"
fi

echo ""
echo "============================================"
echo "  🎉 All services started!"
echo ""
echo "  🌐 Public URLs:"
echo "     TTS:     https://vieneutts.dukyai.com/api/tts"
echo "     Whisper: https://whisper.dukyai.com"
echo ""
echo "  📊 Model: VieNeu-TTS 0.5B (Maximum Quality)"
echo ""
echo "  📝 Logs:"
echo "     TTS:     tail -f /var/log/tts_api.log"
echo "     Whisper: tail -f /var/log/whisper.log"
echo "     Tunnel:  tail -f /var/log/cloudflared.log"
echo ""
echo "  ⏹️  Stop: bash /root/start_all.sh stop"
echo "============================================"
