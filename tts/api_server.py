"""
VieNeu-TTS REST API Server
===========================
FastAPI server wrapping VieNeu-TTS for programmatic TTS access.

Endpoints:
  POST /api/tts        - Synthesize speech from text (returns WAV)
  GET  /api/voices     - List available preset voices
  GET  /api/health     - Health check

Usage:
  uv run python apps/api_server.py
  # or
  uv run uvicorn apps.api_server:app --host 0.0.0.0 --port 8000

Environment variables:
  BACKBONE_REPO     - Model repo (default: pnnbao-ump/VieNeu-TTS-0.3B)
  CODEC_REPO        - Codec repo (default: neuphonic/distill-neucodec)
  BACKBONE_DEVICE   - Device (default: cuda)
  CODEC_DEVICE      - Device for codec (default: cuda)
  DEFAULT_VOICE     - Default voice ID (default: Doan)
  API_PORT          - Server port (default: 8000)
  API_HOST          - Server host (default: 0.0.0.0)
"""

import os
import io
import time
import logging
import tempfile
import numpy as np
import soundfile as sf
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
BACKBONE_REPO = os.getenv("BACKBONE_REPO", "pnnbao-ump/VieNeu-TTS")
CODEC_REPO = os.getenv("CODEC_REPO", "neuphonic/distill-neucodec")
BACKBONE_DEVICE = os.getenv("BACKBONE_DEVICE", "cuda")
CODEC_DEVICE = os.getenv("CODEC_DEVICE", "cuda")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "Doan")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VieNeu-API")

# ---------------------------------------------------------------------------
# Global TTS instance
# ---------------------------------------------------------------------------
tts = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown."""
    global tts
    logger.info("🚀 Loading VieNeu-TTS model (LMDeploy optimized)...")
    logger.info(f"   Backbone: {BACKBONE_REPO}")
    logger.info(f"   Codec:    {CODEC_REPO}")
    logger.info(f"   Device:   {BACKBONE_DEVICE}")

    from vieneu import FastVieNeuTTS
    tts = FastVieNeuTTS(
        backbone_repo=BACKBONE_REPO,
        backbone_device=BACKBONE_DEVICE,
        codec_repo=CODEC_REPO,
        codec_device=CODEC_DEVICE,
        memory_util=0.4,
    )
    logger.info("✅ Model loaded with LMDeploy optimizations!")

    yield  # App runs here

    # Shutdown
    logger.info("🛑 Shutting down, releasing model...")
    if tts is not None:
        tts.close()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VieNeu-TTS API",
    description="Vietnamese Text-to-Speech API powered by VieNeu-TTS",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize", min_length=1, max_length=5000)
    voice: Optional[str] = Field(None, description="Voice ID (e.g. 'Doan', 'Vinh', 'Binh'). Defaults to Đoan.")
    temperature: float = Field(1.0, ge=0.1, le=1.5, description="Generation temperature")
    max_chars_chunk: int = Field(256, ge=64, le=512, description="Max characters per chunk")
    format: str = Field("wav", description="Output format: 'wav'")


class VoiceInfo(BaseModel):
    id: str
    description: str
    ref_text: str


class HealthResponse(BaseModel):
    status: str
    model: str
    default_voice: str
    uptime_seconds: float


# ---------------------------------------------------------------------------
# Startup tracking
# ---------------------------------------------------------------------------
_start_time = time.time()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok" if tts is not None else "loading",
        model=BACKBONE_REPO,
        default_voice=DEFAULT_VOICE,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@app.get("/api/voices", response_model=list[VoiceInfo])
async def list_voices():
    """List all available preset voices."""
    if tts is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    voices = []
    for desc, vid in tts.list_preset_voices():
        # Get the ref text from the voice data
        try:
            voice_data = tts.get_preset_voice(vid)
            ref_text = voice_data.get("text", "")
        except Exception:
            ref_text = ""
        voices.append(VoiceInfo(id=vid, description=desc, ref_text=ref_text))
    return voices


@app.post("/api/tts")
async def synthesize(req: TTSRequest):
    """
    Synthesize speech from text.

    Returns a WAV audio file.
    """
    if tts is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    voice_id = req.voice or DEFAULT_VOICE

    # Verify voice exists
    available_ids = [vid for _, vid in tts.list_preset_voices()]
    if voice_id not in available_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Voice '{voice_id}' not found. Available: {available_ids}"
        )

    start_time = time.time()

    try:
        # Get voice data
        voice_data = tts.get_preset_voice(voice_id)

        # Run inference
        audio_wav = tts.infer(
            text=req.text,
            ref_codes=voice_data["codes"],
            ref_text=voice_data["text"],
            temperature=req.temperature,
            max_chars=req.max_chars_chunk,
        )

        if audio_wav is None or len(audio_wav) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        # Encode to WAV in memory
        buffer = io.BytesIO()
        sf.write(buffer, audio_wav, 24000, format="WAV")
        buffer.seek(0)

        process_time = time.time() - start_time
        duration = len(audio_wav) / 24000

        logger.info(
            f"TTS: voice={voice_id}, text_len={len(req.text)}, "
            f"audio={duration:.2f}s, time={process_time:.2f}s, "
            f"rtf={duration/process_time:.2f}x"
        )

        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav",
                "X-Process-Time": f"{process_time:.3f}",
                "X-Audio-Duration": f"{duration:.3f}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.api_server:app",
        host=API_HOST,
        port=API_PORT,
        workers=1,  # Single worker — model is GPU-bound
        log_level="info",
    )
