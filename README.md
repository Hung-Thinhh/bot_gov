# DukyAI AI Services

TTS (Text-to-Speech) + Whisper (Speech-to-Text) API services.

## Yêu cầu
- Ubuntu 22.04+
- NVIDIA GPU (khuyên dùng A5000 24GB trở lên)
- Domain trên Cloudflare

## Cài đặt nhanh (1 lệnh)

```bash
git clone https://github.com/pnnbao97/dukyai-ai-services.git
cd dukyai-ai-services
bash scripts/setup.sh
```

## Sau khi cài đặt

### Cấu hình Cloudflare Tunnel
```bash
cloudflared tunnel login
cloudflared tunnel create vieneutts
cloudflared tunnel route dns vieneutts vieneutts.dukyai.com
cloudflared tunnel route dns vieneutts whisper.dukyai.com
```

### Khởi động tất cả
```bash
bash /root/start_all.sh
```

### Tắt tất cả
```bash
bash /root/start_all.sh stop
```

## API Endpoints

### TTS (Text-to-Speech)
| Endpoint | Method | Mô tả |
|---|---|---|
| `/api/tts` | POST | Text → WAV audio |
| `/api/voices` | GET | Danh sách giọng |
| `/api/health` | GET | Health check |

**Ví dụ:**
```bash
curl -X POST https://vieneutts.dukyai.com/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Xin chào Việt Nam", "voice": "Doan"}' \
  -o output.wav
```

### Whisper (Speech-to-Text)
| Endpoint | Method | Mô tả |
|---|---|---|
| `/api/transcribe` | POST | Audio → Text |
| `/api/health` | GET | Health check |

**Ví dụ:**
```bash
curl -X POST https://whisper.dukyai.com/api/transcribe \
  -F "file=@audio.wav" \
  -F "language=vi"
```

## Cấu trúc dự án
```
dukyai-ai-services/
├── tts/
│   └── api_server.py       # FastAPI TTS server
├── whisper/
│   └── app.py              # Gradio UI + API Whisper
├── nginx/
│   ├── nginx_tts.conf      # Nginx config cho TTS
│   └── nginx_whisper.conf  # Nginx config cho Whisper
├── scripts/
│   ├── setup.sh            # Auto setup script
│   └── start_all.sh        # Start/stop all services
└── README.md
```

## Giọng có sẵn (TTS)
| Giọng | ID |
|---|---|
| Đoan (nữ miền Nam) | `Doan` |
| Vĩnh (nam miền Nam) | `Vinh` |
| Bình (nam miền Bắc) | `Binh` |
| Ly (nữ miền Bắc) | `Ly` |
| Ngọc (nữ miền Bắc) | `Ngoc` |
