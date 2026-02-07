"""
FastAPI web interface for AI Puzzle MVP.

Operator-facing tool for processing customer orders:
- Upload customer photos
- Select style and describe subject
- Monitor processing with step-by-step progress
- Preview results with quality breakdown and cost
- Submit feedback (rating + comment)
- Download print-ready files

Run: uvicorn web.app:app --reload --port 8000
"""

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

load_dotenv()

from web.jobs import (
    create_job,
    get_feedback,
    get_job,
    list_jobs,
    save_feedback,
    update_job,
)

app = FastAPI(title="AI Puzzle Workshop")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path("uploads")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _parse_metadata(job: dict) -> dict:
    """Parse job metadata from JSON string to dict. Returns empty dict on failure."""
    raw = job.get("metadata", "{}")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return raw if isinstance(raw, dict) else {}


def _process_job(job_id: str):
    """Background task: run the full puzzle pipeline for a job."""
    job = get_job(job_id)
    if not job:
        return

    update_job(job_id, status="processing")

    meta = _parse_metadata(job)
    face_swap_enabled = meta.get("face_swap", True)

    def on_progress(step: int, label: str, total: int):
        """Write step progress into job metadata."""
        current_meta = _parse_metadata(get_job(job_id))
        current_meta["current_step"] = step
        current_meta["current_step_label"] = label
        current_meta["total_steps"] = total
        update_job(job_id, metadata=json.dumps(current_meta))

    try:
        from fulfill_order import fulfill_order

        manifest = fulfill_order(
            photo_path=job["photo_path"],
            style=job["style"],
            subject=job.get("subject", "a smiling person"),
            puzzle_size=job["puzzle_size"],
            order_id=job_id,
            backend=job["backend"],
            skip_consent=False,
            face_swap=face_swap_enabled,
            progress_callback=on_progress,
        )

        # Update job with results — store full manifest in metadata
        order_dir = Path("orders") / job_id
        preview_path = str(order_dir / "preview.jpg")
        print_path = str(order_dir / "print_ready.jpg")

        quality_score = manifest.get("steps", {}).get("quality", {}).get("composite_score", 0)

        # Merge manifest into metadata
        final_meta = _parse_metadata(get_job(job_id))
        final_meta["manifest"] = manifest

        update_job(
            job_id,
            status="completed",
            preview_path=preview_path if Path(preview_path).exists() else None,
            print_ready_path=print_path if Path(print_path).exists() else None,
            quality_score=quality_score,
            metadata=json.dumps(final_meta, default=str),
        )

    except Exception as e:
        update_job(job_id, status="error", error=str(e))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, rerun: str = ""):
    """Upload form + recent jobs list."""
    jobs = list_jobs(limit=20)

    # Parse metadata for each job so templates can access cost/manifest
    for job in jobs:
        job["meta"] = _parse_metadata(job)

    # Handle rerun pre-fill
    rerun_job = None
    if rerun:
        rerun_job = get_job(rerun)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "jobs": jobs,
        "rerun_job": rerun_job,
    })


@app.post("/upload")
async def upload(
    request: Request,
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(None),
    style: str = Form("storybook_cartoon"),
    backend: str = Form("flux_kontext"),
    puzzle_size: int = Form(1000),
    consent: str = Form(...),
    face_swap: str = Form(""),
    existing_photo: str = Form(""),
):
    """Handle photo upload and start processing."""
    job_id = f"WEB-{uuid.uuid4().hex[:8].upper()}"

    # Determine photo path — reuse existing or save new upload
    if existing_photo and Path(existing_photo).exists():
        photo_path = existing_photo
    elif photo and photo.filename:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(photo.filename).suffix or ".jpg"
        photo_path = str(UPLOAD_DIR / f"{job_id}{ext}")
        with open(photo_path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
    else:
        return HTMLResponse("No photo provided", status_code=400)

    # Store face_swap preference in metadata
    meta = {"face_swap": face_swap == "yes"}

    # Create job
    create_job(
        job_id=job_id,
        photo_path=photo_path,
        style=style,
        subject="a smiling person",
        backend=backend,
        puzzle_size=puzzle_size,
        metadata=json.dumps(meta),
    )

    # Start processing in background
    background_tasks.add_task(_process_job, job_id)

    return RedirectResponse(url=f"/status/{job_id}", status_code=303)


@app.get("/status/{job_id}", response_class=HTMLResponse)
async def status(request: Request, job_id: str):
    """Job status page with HTMX polling."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    return templates.TemplateResponse("processing.html", {
        "request": request,
        "job": job,
    })


@app.get("/status/{job_id}/poll", response_class=HTMLResponse)
async def status_poll(request: Request, job_id: str):
    """HTMX polling endpoint - returns updated status fragment."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    # Parse metadata so templates can read step progress
    job["meta"] = _parse_metadata(job)

    if job["status"] == "completed":
        return templates.TemplateResponse("_status_complete.html", {
            "request": request,
            "job": job,
        })
    elif job["status"] == "error":
        return templates.TemplateResponse("_status_error.html", {
            "request": request,
            "job": job,
        })
    else:
        return templates.TemplateResponse("_status_processing.html", {
            "request": request,
            "job": job,
        })


@app.get("/preview/{job_id}", response_class=HTMLResponse)
async def preview(request: Request, job_id: str):
    """Preview page showing original vs generated side-by-side."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    if job["status"] != "completed":
        return RedirectResponse(url=f"/status/{job_id}")

    job["meta"] = _parse_metadata(job)
    feedback = get_feedback(job_id)

    return templates.TemplateResponse("preview.html", {
        "request": request,
        "job": job,
        "feedback": feedback,
    })


@app.post("/feedback/{job_id}")
async def submit_feedback(
    job_id: str,
    rating: int = Form(...),
    comment: str = Form(""),
):
    """Save feedback for a job and redirect back to preview."""
    save_feedback(job_id, rating, comment)
    return RedirectResponse(url=f"/preview/{job_id}", status_code=303)


@app.get("/download/{job_id}/{file_type}")
async def download(job_id: str, file_type: str):
    """Download preview or print-ready file."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    if file_type == "preview" and job.get("preview_path"):
        return FileResponse(
            job["preview_path"],
            filename=f"{job_id}_preview.jpg",
            media_type="image/jpeg",
        )
    elif file_type == "print_ready" and job.get("print_ready_path"):
        return FileResponse(
            job["print_ready_path"],
            filename=f"{job_id}_print_ready.jpg",
            media_type="image/jpeg",
        )
    else:
        return HTMLResponse("File not available", status_code=404)


@app.get("/image/{job_id}/{image_type}")
async def serve_image(job_id: str, image_type: str):
    """Serve job images (original, preview, generated)."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Not found", status_code=404)

    if image_type == "original" and job.get("photo_path"):
        return FileResponse(job["photo_path"])
    elif image_type == "preview" and job.get("preview_path"):
        return FileResponse(job["preview_path"])
    elif image_type == "generated":
        generated = Path("orders") / job_id / "generated.png"
        if generated.exists():
            return FileResponse(str(generated))

    return HTMLResponse("Not found", status_code=404)
