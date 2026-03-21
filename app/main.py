import uuid
import asyncio
import shutil
from pathlib import Path
from collections import OrderedDict

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from app.config import (
    UPLOAD_DIR, STATIC_DIR, DEFAULT_MODEL, DEFAULT_LANGUAGE,
    SUPPORTED_MODELS, SUPPORTED_AUDIO_EXTENSIONS, SUPPORTED_LANGUAGES,
    EXPORT_FORMATS, HOST, PORT,
)
from app.transcriber import transcribe
from app.subtitles import FORMATTERS

app = FastAPI(title="Whisper Local STT")

# Job storage (in-memory, ordered)
jobs: OrderedDict[str, dict] = OrderedDict()
job_queue: asyncio.Queue = asyncio.Queue()
_worker_started = False


def _cleanup_old_jobs():
    """Keep only the most recent 100 jobs."""
    while len(jobs) > 100:
        _, old = jobs.popitem(last=False)
        upload = old.get("upload_path")
        if upload and Path(upload).exists():
            Path(upload).unlink(missing_ok=True)


async def _process_jobs():
    """Background worker that processes transcription jobs sequentially."""
    while True:
        job_id = await job_queue.get()
        job = jobs.get(job_id)
        if not job or job["status"] == "failed":
            job_queue.task_done()
            continue

        job["status"] = "processing"
        try:
            result = await asyncio.to_thread(
                transcribe,
                audio_path=job["upload_path"],
                model_size=job["model"],
                language=job["language"],
            )
            job["status"] = "complete"
            job["result"] = result
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
        finally:
            # Clean up uploaded file
            upload = Path(job["upload_path"])
            if upload.exists():
                upload.unlink(missing_ok=True)
            job_queue.task_done()
            _cleanup_old_jobs()


@app.on_event("startup")
async def startup():
    global _worker_started
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not _worker_started:
        asyncio.create_task(_process_jobs())
        _worker_started = True


@app.post("/api/transcribe")
async def api_transcribe(
    file: UploadFile = File(...),
    model: str = Form(DEFAULT_MODEL),
    language: str = Form(DEFAULT_LANGUAGE),
):
    # Validate model
    if model not in SUPPORTED_MODELS:
        raise HTTPException(400, f"Unsupported model: {model}. Choose from {SUPPORTED_MODELS}")

    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}. Supported: {sorted(SUPPORTED_AUDIO_EXTENSIONS)}")

    # Save upload
    job_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / f"{job_id}{ext}"
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create job
    jobs[job_id] = {
        "status": "queued",
        "model": model,
        "language": language,
        "source_filename": Path(file.filename or "audio").stem,
        "upload_path": str(upload_path),
        "result": None,
        "error": None,
    }
    await job_queue.put(job_id)

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/status/{job_id}")
async def api_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "complete":
        response["result"] = job["result"]
    elif job["status"] == "failed":
        response["error"] = job["error"]
    return response


@app.get("/api/download/{job_id}/{fmt}")
async def api_download(job_id: str, fmt: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "complete":
        raise HTTPException(400, "Job not complete")
    if fmt not in FORMATTERS:
        raise HTTPException(400, f"Unsupported format: {fmt}. Choose from {list(FORMATTERS.keys())}")

    formatter, content_type = FORMATTERS[fmt]
    content = formatter(job["result"]["segments"])
    filename = f"{job['source_filename']}.{fmt}"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/config")
async def api_config():
    return {
        "models": SUPPORTED_MODELS,
        "default_model": DEFAULT_MODEL,
        "languages": SUPPORTED_LANGUAGES,
        "default_language": DEFAULT_LANGUAGE,
        "supported_formats": sorted(SUPPORTED_AUDIO_EXTENSIONS),
        "export_formats": EXPORT_FORMATS,
    }


# Serve static files and web UI
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
