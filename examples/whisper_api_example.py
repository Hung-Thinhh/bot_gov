#!/usr/bin/env python3
"""
Ví dụ gọi API Whisper từ Python
===============================
Cách chạy:
    python whisper_api_example.py

Yêu cầu:
    pip install requests
"""

import requests
import json
from pathlib import Path

# ============================================
# CẤU HÌNH
# ============================================
API_URL = "https://whisper.dukyai.com/api/transcribe"
HEALTH_URL = "https://whisper.dukyai.com/api/health"

# ============================================
# 1. KIỂM TRA API CÓ HOẠT ĐỘNG KHÔNG
# ============================================
print("=" * 50)
print("1. KIỂM TRA HEALTH CHECK")
print("=" * 50)

try:
    response = requests.get(HEALTH_URL, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Lỗi: {e}")

# ============================================
# 2. TẠO FILE AUDIO MẪU (nếu chưa có)
# ============================================
print("\n" + "=" * 50)
print("2. TẠO FILE AUDIO MẪU")
print("=" * 50)

test_file = "/tmp/test_whisper.wav"

# Tạo file wav mẫu (3 giây sine wave)
import subprocess
subprocess.run([
    "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=500:duration=3",
    "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
    test_file, "-y"
], capture_output=True)

print(f"Đã tạo file: {test_file}")

# ============================================
# 3. GỌI API TRANSCRIBE
# ============================================
print("\n" + "=" * 50)
print("3. GỌI API TRANSCRIBE")
print("=" * 50)

# MỞ FILE ĐỂ UPLOAD
with open(test_file, "rb") as audio_file:
    # CHUẨN BỊ DATA
    files = {
        "file": ("test_audio.wav", audio_file, "audio/wav")
    }
    data = {
        "language": "vi",      # Ngôn ngữ: vi, en, auto
        "task": "transcribe"   # transcribe hoặc translate
    }
    
    print(f"\n📤 Đang gửi file đến: {API_URL}")
    print(f"   File: {test_file}")
    print(f"   Language: vi")
    
    # GỬI REQUEST
    try:
        response = requests.post(
            API_URL,
            files=files,
            data=data,
            timeout=120  # 2 phút timeout
        )
        
        print(f"\n📥 STATUS CODE: {response.status_code}")
        
        # ============================================
        # 4. XỬ LÝ RESPONSE
        # ============================================
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "=" * 50)
            print("RESPONSE TRẢ VỀ:")
            print("=" * 50)
            
            # In toàn bộ JSON đẹp
            print(f"\n📋 JSON đầy đủ:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # In từng field
            print(f"\n📝 Các trường dữ liệu:")
            print(f"   • text: \"{result['text']}\"")
            print(f"   • language: {result['language']}")
            print(f"   • language_probability: {result['language_probability']}")
            print(f"   • duration: {result['duration']} giây")
            print(f"   • process_time: {result['process_time']} giây")
            
            # In segments (chi tiết từng đoạn)
            if result['segments']:
                print(f"\n🔍 Chi tiết từng đoạn (segments):")
                for i, seg in enumerate(result['segments'], 1):
                    print(f"   [{i}] [{seg['start']}s → {seg['end']}s]: \"{seg['text']}\"")
            else:
                print("\n⚠️  Không có segments (file không có lỜi nói)")
                
        else:
            print(f"\n❌ LỖI: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("\n❌ Timeout: Request quá lâu")
    except requests.exceptions.ConnectionError:
        print("\n❌ Không kết nối được đến server")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")

# ============================================
# 5. VÍ DỤ VỚI FILE MP3
# ============================================
print("\n" + "=" * 50)
print("5. VÍ DỤ VỚI FILE MP3")
print("=" * 50)

mp3_example = """
import requests

url = "https://whisper.dukyai.com/api/transcribe"

with open("audio.mp3", "rb") as f:
    files = {"file": ("audio.mp3", f, "audio/mpeg")}
    data = {"language": "vi"}
    
    response = requests.post(url, files=files, data=data)
    result = response.json()
    
    print(f"Text: {result['text']}")
    print(f"Language: {result['language']}")
"""

print(mp3_example)

# ============================================
# 6. CLASS WRAPPER
# ============================================
print("\n" + "=" * 50)
print("6. CLASS WRAPPER (DÙNG CHO PROJECT)")
print("=" * 50)

wrapper_code = '''
import requests
from typing import Optional, Dict, Any

class WhisperAPI:
    def __init__(self, base_url: str = "https://whisper.dukyai.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/transcribe"
    
    def transcribe(self, file_path: str, language: str = "vi") -> Dict[str, Any]:
        """
        Gọi API transcribe
        
        Args:
            file_path: Đường dẫn file audio (.wav, .mp3, .m4a)
            language: vi (Tiếng Việt), en (English), auto (Tự động)
        
        Returns:
            {
                "text": "nội dung nhận dạng được",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "xin chào"}
                ],
                "language": "vi",
                "language_probability": 0.98,
                "duration": 10.5,
                "process_time": 0.5
            }
        """
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"language": language}
            
            response = requests.post(
                self.api_url,
                files=files,
                data=data,
                timeout=300
            )
            response.raise_for_status()
            return response.json()

# Sử dụng:
# client = WhisperAPI()
# result = client.transcribe("audio.wav", language="vi")
# print(result["text"])
'''

print(wrapper_code)

print("\n" + "=" * 50)
print("HOÀN TẤT!")
print("=" * 50)
