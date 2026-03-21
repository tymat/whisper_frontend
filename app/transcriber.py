import os
import tempfile
import subprocess
from pathlib import Path
from pywhispercpp.model import Model

from app.config import FFMPEG_PATH

MODELS_DIR = Path(__file__).parent.parent / "models"
SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"]


def get_model_path(model_size: str) -> Path:
    """Return the expected path for a given model size."""
    return MODELS_DIR / f"ggml-{model_size}.bin"


def ensure_model(model_size: str) -> Path:
    """Download model if not cached, return path."""
    if model_size not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model: {model_size}. Choose from {SUPPORTED_MODELS}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = get_model_path(model_size)
    if model_path.exists():
        return model_path
    # pywhispercpp auto-downloads when given model name
    # We load once to trigger the download, then return the path
    Model(model_size, models_dir=str(MODELS_DIR))
    if not model_path.exists():
        # Fallback: check for alternative naming
        for f in MODELS_DIR.iterdir():
            if model_size in f.name and f.suffix == ".bin":
                return f
    return model_path


def convert_to_wav(input_path: str) -> str:
    """Convert audio file to 16kHz mono WAV for whisper. Returns path to WAV file."""
    ext = Path(input_path).suffix.lower()
    if ext == ".wav":
        return input_path

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        subprocess.run(
            [
                FFMPEG_PATH, "-y", "-i", input_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                tmp.name,
            ],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        os.unlink(tmp.name)
        raise RuntimeError(f"ffmpeg not found at {FFMPEG_PATH}")
    except subprocess.CalledProcessError as e:
        os.unlink(tmp.name)
        raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode()}")
    return tmp.name


def transcribe(
    audio_path: str,
    model_size: str = "base",
    language: str = "auto",
) -> dict:
    """
    Transcribe an audio file using whisper.cpp with Metal acceleration.

    Always returns dict with 'text' and 'segments' (for subtitle export).
    """
    ensure_model(model_size)

    wav_path = convert_to_wav(audio_path)
    converted = wav_path != audio_path

    try:
        model = Model(model_size, models_dir=str(MODELS_DIR))

        params = {}
        if language and language != "auto":
            params["language"] = language

        segments = model.transcribe(wav_path, **params)

        result_segments = []
        full_text_parts = []
        for seg in segments:
            result_segments.append({
                "start": seg.t0 / 100.0,
                "end": seg.t1 / 100.0,
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text.strip())

        return {
            "text": " ".join(full_text_parts),
            "segments": result_segments,
        }

    finally:
        if converted and os.path.exists(wav_path):
            os.unlink(wav_path)
