#!/bin/bash
# ============================================
# DukyAI Services — One-Click Setup
# ============================================
# Chạy trên Ubuntu 22.04 với GPU NVIDIA
# Usage: bash setup.sh
# ============================================

set -e

echo "============================================"
echo "  DukyAI AI Services — Auto Setup"
echo "============================================"

# --- 1. System packages ---
echo "[1/7] Installing system packages..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git curl build-essential nginx > /dev/null 2>&1

# Fix timezone
rm -rf /etc/localtime
ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime

# --- 2. Install UV ---
echo "[2/7] Installing UV..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# --- 3. Clone and setup VieNeu-TTS ---
echo "[3/7] Setting up VieNeu-TTS..."
if [ ! -d "/root/VieNeu-TTS" ]; then
    cd /root
    git clone https://github.com/pnnbao97/VieNeu-TTS.git
fi
cd /root/VieNeu-TTS
uv sync
uv pip install fastapi "uvicorn[standard]"

# Copy API server
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/../tts/api_server.py" /root/VieNeu-TTS/apps/api_server.py

# --- 4. Setup Whisper ---
echo "[4/7] Setting up Whisper..."
mkdir -p /root/whisper-api
cp "$SCRIPT_DIR/../whisper/app.py" /root/whisper-api/app.py
cd /root/whisper-api
if [ ! -f "pyproject.toml" ]; then
    uv init
fi
uv add faster-whisper gradio

# --- 5. Setup Nginx ---
echo "[5/7] Configuring Nginx..."
cp "$SCRIPT_DIR/../nginx/nginx_tts.conf" /etc/nginx/sites-available/vieneutts
cp "$SCRIPT_DIR/../nginx/nginx_whisper.conf" /etc/nginx/sites-available/whisper
ln -sf /etc/nginx/sites-available/vieneutts /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/whisper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# --- 6. Install Cloudflared ---
echo "[6/7] Installing Cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
        -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
fi

# --- 7. Copy startup script ---
echo "[7/7] Setting up startup script..."
cp "$SCRIPT_DIR/start_all.sh" /root/start_all.sh
chmod +x /root/start_all.sh

echo ""
echo "============================================"
echo "  ✅ Setup hoàn tất!"
echo ""
echo "  Bước tiếp theo:"
echo "  1. cloudflared tunnel login"
echo "  2. cloudflared tunnel create vieneutts"
echo "  3. cloudflared tunnel route dns vieneutts vieneutts.dukyai.com"
echo "  4. cloudflared tunnel route dns vieneutts whisper.dukyai.com"
echo "  5. bash /root/start_all.sh"
echo "============================================"
