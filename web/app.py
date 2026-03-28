"""
FastAPI web interface for AI Puzzle MVP.

Step-by-step wizard for the 5-step puzzle generation pipeline:
1. Upload & describe person
2. Background removal ($0.01)
3. Character generation ($0.08)
4. Costume ($0.08)
5. Scene + 3 compositing methods ($0.32)

Run: python3 -m uvicorn web.app:app --reload --port 8000
"""

import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_metadata(job: dict) -> dict:
    """Parse job metadata from JSON string to dict. Returns empty dict on failure."""
    raw = job.get("metadata", "{}")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return raw if isinstance(raw, dict) else {}


def _get_step_data(meta: dict, step: int) -> dict:
    """Get the data for a specific wizard step from metadata."""
    return meta.get("steps", {}).get(str(step), {})


def _total_cost(meta: dict) -> float:
    """Calculate total cost from all completed steps."""
    total = 0
    for step_data in meta.get("steps", {}).values():
        if isinstance(step_data, dict):
            total += step_data.get("cost", 0)
    return round(total, 3)


# ---------------------------------------------------------------------------
# Wizard: Background task runner
# ---------------------------------------------------------------------------

def _run_wizard_step(job_id: str, step: int):
    """Background task: run a single pipeline step for a wizard job."""
    job = get_job(job_id)
    if not job:
        return

    meta = _parse_metadata(job)
    order_dir = Path("orders") / job_id
    steps = meta.setdefault("steps", {})

    # Don't re-run if already complete or processing
    step_data = steps.get(str(step), {})
    if step_data.get("status") in ("complete", "processing"):
        return

    # Mark step as processing
    steps[str(step)] = {"status": "processing"}
    meta["current_step"] = step
    update_job(job_id, status="processing", metadata=json.dumps(meta, default=str))

    try:
        from pipeline_steps import (
            step_remove_background,
            step_generate_character,
            step_costume,
            step_composite,
            save_manifest,
        )

        if step == 2:
            input_path = steps["1"]["input_prepared"]
            result = step_remove_background(input_path, str(order_dir))

        elif step == 3:
            bg_removed = steps["2"]["bg_removed"]
            result = step_generate_character(
                bg_removed_path=bg_removed,
                subject=meta.get("subject", "a smiling person"),
                gender=meta.get("gender", "person"),
                scene=meta.get("scene", "village"),
                order_dir=str(order_dir),
                seed=meta.get("seed"),
            )

        elif step == 4:
            character = steps["3"]["character"]
            result = step_costume(
                character_path=character,
                scene=meta.get("scene", "village"),
                order_dir=str(order_dir),
                seed=meta.get("seed"),
            )

        elif step == 5:
            costumed = steps["4"]["costumed"]

            def on_sub_progress(sub_step, label, sub_total):
                """Update sub-step progress in metadata."""
                current_meta = _parse_metadata(get_job(job_id))
                step5 = current_meta.get("steps", {}).get("5", {})
                step5["sub_step"] = sub_step
                step5["sub_label"] = label
                step5["sub_total"] = sub_total
                current_meta.setdefault("steps", {})["5"] = step5
                update_job(job_id, metadata=json.dumps(current_meta, default=str))

            result = step_composite(
                costumed_path=costumed,
                scene=meta.get("scene", "village"),
                order_dir=str(order_dir),
                seed=meta.get("seed"),
                progress_callback=on_sub_progress,
            )
        else:
            return

        # Re-read metadata (may have been updated by sub-progress callbacks)
        meta = _parse_metadata(get_job(job_id))
        steps = meta.setdefault("steps", {})

        # Store result and mark complete
        steps[str(step)] = {**result, "status": "complete"}
        meta["total_cost"] = _total_cost(meta)

        if step == 5:
            # Final step — save manifest and mark job completed
            save_manifest(str(order_dir), meta)
            update_job(job_id, status="completed", metadata=json.dumps(meta, default=str))
        else:
            update_job(job_id, status="pending", metadata=json.dumps(meta, default=str))

    except Exception as e:
        # Re-read metadata and mark step as error
        meta = _parse_metadata(get_job(job_id))
        steps = meta.setdefault("steps", {})
        steps[str(step)] = {"status": "error", "error": str(e)}
        update_job(job_id, status="error", error=str(e), metadata=json.dumps(meta, default=str))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard with Start New Puzzle button + recent jobs."""
    jobs = list_jobs(limit=20)
    for job in jobs:
        job["meta"] = _parse_metadata(job)
    return templates.TemplateResponse(name="index.html", context={
        "request": request,
        "jobs": jobs,
    })


# ---------------------------------------------------------------------------
# Wizard: Step 1 — Upload
# ---------------------------------------------------------------------------

@app.get("/wizard/new", response_class=HTMLResponse)
async def wizard_new(request: Request):
    """Show the upload form (Step 1)."""
    return templates.TemplateResponse(name="wizard_step1_upload.html", context={
        "request": request,
        "current_step": 1,
        "total_cost": 0,
    })


@app.post("/wizard/start")
async def wizard_start(
    request: Request,
    photo: UploadFile = File(...),
    consent: str = Form(...),
    subject: str = Form(""),
    seed: Optional[str] = Form(""),
    # Structured subject fields
    age_range: str = Form(""),
    gender: str = Form(""),
    ethnicity: str = Form(""),
    hair_color: str = Form(""),
    hair_style: str = Form(""),
    skin_tone: str = Form(""),
    extras: str = Form(""),
):
    """Handle photo upload, validate, and redirect to Step 2."""
    from pipeline_steps import step_validate_and_prepare

    job_id = f"WEB-{uuid.uuid4().hex[:8].upper()}"
    order_dir = Path("orders") / job_id
    order_dir.mkdir(parents=True, exist_ok=True)

    # Validate file type early
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(photo.filename).suffix or ".jpg"
    allowed = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
    if ext.lower() not in allowed:
        return HTMLResponse(
            f"Unsupported file type '{ext}'. Please upload a JPEG, PNG, or HEIC image.",
            status_code=400,
        )

    # Save uploaded photo
    photo_path = str(UPLOAD_DIR / f"{job_id}{ext}")
    with open(photo_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    # Validate and prepare first (converts HEIC → JPEG if needed)
    result = step_validate_and_prepare(photo_path, str(order_dir))

    # Auto-detect skin tone from the prepared image (not the HEIC original)
    # Gracefully skips if OpenCV is not available (e.g. Render lightweight mode)
    if not skin_tone:
        try:
            from subject_builder import detect_skin_tone
            detected = detect_skin_tone(result["input_prepared"])
            if detected:
                skin_tone = detected
                print(f"  Auto-detected skin tone: {skin_tone}")
        except ImportError:
            pass

    # Build subject description
    final_subject = subject.strip()
    if not final_subject and (age_range or gender or hair_color or hair_style or ethnicity):
        from subject_builder import build_subject_description
        final_subject = build_subject_description(
            age_range=age_range or "child",
            gender=gender or "person",
            ethnicity=ethnicity,
            hair_color=hair_color,
            hair_style=hair_style,
            skin_tone=skin_tone,
            extras=extras,
        )
    if not final_subject:
        final_subject = "a smiling person"

    # Parse seed
    parsed_seed = None
    if seed and seed.strip():
        try:
            parsed_seed = int(seed.strip())
        except ValueError:
            pass

    # Build initial metadata
    meta = {
        "scene": "village",
        "subject": final_subject,
        "gender": gender or "person",
        "current_step": 2,
        "steps": {
            "1": {**result, "status": "complete"},
        },
        "total_cost": 0,
    }
    if parsed_seed is not None:
        meta["seed"] = parsed_seed

    # Create job
    create_job(
        job_id=job_id,
        photo_path=photo_path,
        style="village",
        subject=final_subject,
        backend="flux_kontext_max",
        metadata=json.dumps(meta, default=str),
    )

    return RedirectResponse(url=f"/wizard/{job_id}/step/2", status_code=303)


# ---------------------------------------------------------------------------
# Wizard: Step pages (GET), processing triggers (POST), polling (GET)
# ---------------------------------------------------------------------------

STEP_TEMPLATES = {
    2: "wizard_step2_bgremoval.html",
    3: "wizard_step3_character.html",
    4: "wizard_step4_costume.html",
    5: "wizard_step5_composite.html",
}


@app.get("/wizard/{job_id}/step/{step}", response_class=HTMLResponse)
async def wizard_step(request: Request, job_id: str, step: int):
    """Render a wizard step page."""
    job = get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)

    if step not in STEP_TEMPLATES:
        return RedirectResponse(url=f"/wizard/{job_id}/step/2", status_code=303)

    meta = _parse_metadata(job)
    job["meta"] = meta
    step_data = _get_step_data(meta, step)

    return templates.TemplateResponse(name=STEP_TEMPLATES[step], context={
        "request": request,
        "job_id": job_id,
        "job": job,
        "step_data": step_data if step_data else None,
        "current_step": step,
        "total_cost": _total_cost(meta),
    })


@app.post("/wizard/{job_id}/step/{step}/run")
async def wizard_step_run(
    job_id: str,
    step: int,
    background_tasks: BackgroundTasks,
):
    """Trigger background processing for a wizard step."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    meta = _parse_metadata(job)
    step_data = _get_step_data(meta, step)

    # Idempotent: don't re-run if already complete or processing
    if step_data.get("status") in ("complete", "processing"):
        return HTMLResponse("", status_code=204)

    background_tasks.add_task(_run_wizard_step, job_id, step)
    return HTMLResponse("", status_code=204)


@app.get("/wizard/{job_id}/step/{step}/poll", response_class=HTMLResponse)
async def wizard_step_poll(request: Request, job_id: str, step: int):
    """HTMX polling endpoint — returns status fragment for a wizard step."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    meta = _parse_metadata(job)
    step_data = _get_step_data(meta, step)
    status = step_data.get("status", "pending")

    return templates.TemplateResponse(name="_wizard_poll.html", context={
        "request": request,
        "job_id": job_id,
        "step": step,
        "status": status,
        "error": step_data.get("error", ""),
        "sub_step": step_data.get("sub_step"),
        "sub_label": step_data.get("sub_label"),
        "sub_total": step_data.get("sub_total"),
        "label": {
            2: "Removing background...",
            3: "Generating Pixar character...",
            4: "Adding costume...",
            5: "Generating scene and composites...",
        }.get(step, "Processing..."),
    })


# ---------------------------------------------------------------------------
# Wizard: Download
# ---------------------------------------------------------------------------

@app.get("/wizard/{job_id}/download/final")
async def wizard_download_final(job_id: str):
    """Download the final puzzle image."""
    path = Path("orders") / job_id / "final.png"
    if path.exists():
        return FileResponse(str(path), filename=f"{job_id}_puzzle.png", media_type="image/png")
    return HTMLResponse("File not available", status_code=404)


# ---------------------------------------------------------------------------
# Wizard: Image serving
# ---------------------------------------------------------------------------

IMAGE_FILES = {
    "input_prepared": "input_prepared.png",
    "bg_removed": "bg_removed.jpg",
    "character": "character.png",
    "costumed": "costumed.png",
    "scene": "scene.png",
    "final": "final.png",
}


@app.get("/wizard/{job_id}/image/{image_type}")
async def wizard_image(job_id: str, image_type: str):
    """Serve intermediate images from the order directory."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Not found", status_code=404)

    # Check order directory first
    if image_type in IMAGE_FILES:
        path = Path("orders") / job_id / IMAGE_FILES[image_type]
        if path.exists():
            return FileResponse(str(path))

    # Fall back to original photo
    if image_type == "original" and job.get("photo_path"):
        return FileResponse(job["photo_path"])

    return HTMLResponse("Not found", status_code=404)


# ---------------------------------------------------------------------------
# Legacy routes (backwards compat for old jobs)
# ---------------------------------------------------------------------------

def _process_job(job_id: str):
    """Background task: generate a Pixar-style character for a job (legacy)."""
    job = get_job(job_id)
    if not job:
        return

    update_job(job_id, status="processing")

    meta = _parse_metadata(job)
    job_seed = meta.get("seed")

    def on_progress(step: int, label: str, total: int):
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
            order_id=job_id,
            backend=job["backend"],
            seed=job_seed,
            progress_callback=on_progress,
        )

        order_dir = Path("orders") / job_id
        preview_path = str(order_dir / "preview.jpg")

        final_meta = _parse_metadata(get_job(job_id))
        final_meta["manifest"] = manifest

        update_job(
            job_id,
            status="completed",
            preview_path=preview_path if Path(preview_path).exists() else None,
            metadata=json.dumps(final_meta, default=str),
        )

    except Exception as e:
        update_job(job_id, status="error", error=str(e))


@app.get("/status/{job_id}", response_class=HTMLResponse)
async def status(request: Request, job_id: str):
    """Job status page with HTMX polling (legacy)."""
    job = get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(name="processing.html", context={
        "request": request,
        "job": job,
    })


@app.get("/status/{job_id}/poll", response_class=HTMLResponse)
async def status_poll(request: Request, job_id: str):
    """HTMX polling endpoint (legacy)."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse(
            '<article><h3>Job not found</h3>'
            '<p>This job may have been lost due to a server restart. '
            '<a href="/">Go back to dashboard</a> to start a new one.</p></article>',
            status_code=286,
        )

    job["meta"] = _parse_metadata(job)

    if job["status"] == "completed":
        return templates.TemplateResponse(name="_status_complete.html", context={
            "request": request,
            "job": job,
        })
    elif job["status"] == "error":
        return templates.TemplateResponse(name="_status_error.html", context={
            "request": request,
            "job": job,
        })
    else:
        return templates.TemplateResponse(name="_status_processing.html", context={
            "request": request,
            "job": job,
        })


@app.get("/preview/{job_id}", response_class=HTMLResponse)
async def preview(request: Request, job_id: str):
    """Preview page (legacy)."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    if job["status"] != "completed":
        return RedirectResponse(url=f"/status/{job_id}")

    job["meta"] = _parse_metadata(job)
    feedback = get_feedback(job_id)

    return templates.TemplateResponse(name="preview.html", context={
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
    """Save feedback (legacy)."""
    save_feedback(job_id, rating, comment)
    return RedirectResponse(url=f"/preview/{job_id}", status_code=303)


@app.get("/download/{job_id}/{file_type}")
async def download(job_id: str, file_type: str):
    """Download preview file (legacy)."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    if file_type == "preview" and job.get("preview_path"):
        return FileResponse(
            job["preview_path"],
            filename=f"{job_id}_preview.jpg",
            media_type="image/jpeg",
        )
    else:
        return HTMLResponse("File not available", status_code=404)


@app.get("/image/{job_id}/{image_type}")
async def serve_image(job_id: str, image_type: str):
    """Serve job images (legacy)."""
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
