from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = Path(__file__).parent / "static"

DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "auto"
HOST = "0.0.0.0"
PORT = 8787

SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"]
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".wma", ".mp4"}
FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"
EXPORT_FORMATS = ["srt", "vtt", "ass", "txt"]

SUPPORTED_LANGUAGES = [
    "auto", "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ru",
    "zh", "ja", "ko", "ar", "hi", "tr", "vi", "th", "sv", "da",
    "no", "fi", "cs", "ro", "hu", "el", "he", "id", "ms", "uk",
]
