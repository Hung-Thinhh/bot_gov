"""
Whisper Speech-to-Text — UI + API (Single Server)
===================================================
Runs Gradio UI and REST API on the same port (7861).

UI:  https://whisper.dukyai.com/
API: POST https://whisper.dukyai.com/api/transcribe
     GET  https://whisper.dukyai.com/api/health
"""
import os
import io
import time
import logging
import tempfile
import gradio as gr
from faster_whisper import WhisperModel
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# ---- Config ----
MODEL_SIZE = os.getenv("WHISPER_MODEL", "medium")
DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE", "float16")
PORT = int(os.getenv("WHISPER_PORT", "7861"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Whisper-API")

print(f"🚀 Loading Whisper model: {MODEL_SIZE} on {DEVICE} ({COMPUTE_TYPE})...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("✅ Model loaded!")

_start_time = time.time()


# ===========================================================
# Common transcription logic
# ===========================================================
def do_transcribe(audio_path, language="vi", task="transcribe"):
    lang = language if language != "auto" else None
    segments, info = model.transcribe(
        audio_path,
        language=lang,
        task=task,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    result_segments = []
    full_text = []
    for seg in segments:
        result_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        full_text.append(seg.text.strip())
    return result_segments, full_text, info


# ===========================================================
# Gradio UI
# ===========================================================
def transcribe_ui(audio_path, language="vi", task="transcribe"):
    if audio_path is None:
        return "⚠️ Vui lòng upload hoặc ghi âm audio.", ""

    start = time.time()
    result_segments, full_text, info = do_transcribe(audio_path, language, task)
    elapsed = time.time() - start

    lines = [f"[{s['start']:.1f}s → {s['end']:.1f}s]  {s['text']}" for s in result_segments]
    header = (
        f"🎯 Ngôn ngữ: {info.language} (xác suất: {info.language_probability:.0%})\n"
        f"⏱️ Thời gian: {elapsed:.1f}s | Độ dài audio: {info.duration:.1f}s\n"
        f"{'─' * 50}\n"
    )
    return header + "\n".join(lines), " ".join(full_text)


with gr.Blocks(title="Whisper STT") as ui:
    gr.Markdown("# 🎙️ Whisper Speech-to-Text")
    gr.Markdown(f"Model: **{MODEL_SIZE}** | GPU: **{DEVICE}** | Compute: **{COMPUTE_TYPE}**")

    with gr.Row():
        with gr.Column(scale=1):
            audio_input = gr.Audio(
                label="🎤 Upload hoặc ghi âm",
                type="filepath",
                sources=["upload", "microphone"],
            )
            with gr.Row():
                language = gr.Dropdown(
                    choices=["vi", "en", "auto"], value="vi", label="Ngôn ngữ",
                )
                task_input = gr.Dropdown(
                    choices=["transcribe", "translate"], value="transcribe", label="Tác vụ",
                )
            btn = gr.Button("🚀 Nhận dạng", variant="primary", size="lg")

        with gr.Column(scale=1):
            output_detail = gr.Textbox(label="📝 Kết quả chi tiết", lines=12)
            output_text = gr.Textbox(label="📋 Text thuần", lines=3)

    btn.click(fn=transcribe_ui, inputs=[audio_input, language, task_input], outputs=[output_detail, output_text])


# ===========================================================
# Mount API routes onto Gradio's FastAPI app
# ===========================================================
app = ui.app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@app.post("/api/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    language: Optional[str] = Form("vi"),
    task: Optional[str] = Form("transcribe"),
):
    suffix = os.path.splitext(file.filename or "audio.wav")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        start = time.time()
        result_segments, full_text, info = do_transcribe(tmp_path, language, task)
        elapsed = time.time() - start

        logger.info(
            f"STT: lang={info.language}, audio={info.duration:.1f}s, "
            f"time={elapsed:.1f}s, segments={len(result_segments)}"
        )

        return {
            "text": " ".join(full_text),
            "segments": result_segments,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2),
            "process_time": round(elapsed, 2),
        }
    except Exception as e:
        logger.error(f"STT error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


# ===========================================================
# Main
# ===========================================================
if __name__ == "__main__":
    ui.launch(server_name="0.0.0.0", server_port=PORT, root_path="https://whisper.dukyai.com")
