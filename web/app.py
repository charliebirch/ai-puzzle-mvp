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
import random
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
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


def _render(request: Request, template: str, context: dict = None) -> HTMLResponse:
    """Render a template, compatible with both old and new Starlette API."""
    ctx = context or {}
    try:
        # New Starlette (1.0+): request is first positional arg
        return templates.TemplateResponse(request, template, ctx)
    except TypeError:
        # Old Starlette: request goes inside context dict
        ctx["request"] = request
        return templates.TemplateResponse(template, ctx)


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
            step_normalize_portrait,
            step_generate_character,
            step_costume,
            step_composite,
            step_upscale_final,
            save_manifest,
        )

        if step == 2:
            input_path = steps["1"]["input_prepared"]
            result = step_remove_background(input_path, str(order_dir))
            # Normalise portrait to front-facing before character generation.
            # Removes props, standardises framing, gives consistent input.
            # Skippable via NORMALIZE_PORTRAIT=0 env var.
            norm_result = step_normalize_portrait(
                bg_removed_path=result["bg_removed"],
                order_dir=str(order_dir),
                seed=meta.get("seed"),
            )
            result["normalized"] = norm_result["normalized"]
            result["cost"] = result.get("cost", 0) + norm_result["cost"]

        elif step == 3:
            step2_data = steps["2"]
            # Use normalised portrait if available; fall back to bg_removed
            character_input = step2_data.get("normalized") or step2_data["bg_removed"]
            result = step_generate_character(
                bg_removed_path=character_input,
                subject=meta.get("subject", "the person in the input image"),
                gender=meta.get("gender", "person"),
                scene=meta.get("scene", "village"),
                order_dir=str(order_dir),
                seed=meta.get("seed"),
                age_range=meta.get("age_range", "adult"),
            )

        elif step == 4:
            character = steps["3"]["character"]
            result = step_costume(
                character_path=character,
                scene=meta.get("scene", "village"),
                order_dir=str(order_dir),
                seed=meta.get("seed"),
                outfit_id=meta.get("outfit_id"),
                subject=meta.get("subject"),
                age_range=meta.get("age_range", "adult"),
                gender=meta.get("gender", "person"),
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
            # Candidates generated — wait for user to pick before completing
            update_job(job_id, status="pending", metadata=json.dumps(meta, default=str))
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
    return _render(request, "index.html", {"jobs": jobs})


# ---------------------------------------------------------------------------
# API: Attribute detection
# ---------------------------------------------------------------------------

@app.post("/api/detect-attributes")
async def api_detect_attributes(photo: UploadFile = File(...)):
    """Detect person attributes from an uploaded photo using Claude vision.

    Called client-side when the user selects a photo, before form submission.
    Returns detected attributes as JSON so the frontend can pre-populate dropdowns.
    Fails gracefully — returns {} if detection unavailable (no API key, etc).
    """
    import tempfile

    ext = Path(photo.filename).suffix.lower() if photo.filename else ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
        ext = ".jpg"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(photo.file, tmp)
        tmp_path = tmp.name

    try:
        # Image resize safety lives inside detect_attributes() now — it
        # auto-downscales oversized inputs to stay under Claude's 5 MB
        # base64 payload limit.
        from detect_attributes import detect_attributes
        attrs = detect_attributes(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return JSONResponse(attrs)


# ---------------------------------------------------------------------------
# Wizard: Step 1 — Upload
# ---------------------------------------------------------------------------

@app.get("/wizard/new", response_class=HTMLResponse)
async def wizard_new(request: Request):
    """Show the upload form (Step 1)."""
    return _render(request, "wizard_step1_upload.html", {
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
    puzzle_size: str = Form("252pc"),
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

    # Subject description: use the input image as identity reference only.
    # Detected attributes (age, gender, ethnicity, hair, skin) are shown in the UI
    # dropdowns for information but NOT injected into generation prompts — text
    # descriptions of appearance make outputs look generic rather than preserving
    # the person's actual likeness from the image.
    final_subject = "the person in the input image"

    # Parse seed
    parsed_seed = None
    if seed and seed.strip():
        try:
            parsed_seed = int(seed.strip())
        except ValueError:
            pass

    # Validate puzzle size
    if puzzle_size not in ("110pc", "252pc"):
        puzzle_size = "252pc"

    # Use detected age_range + gender for prompt file selection only.
    # Toddlers/children get age-appropriate prompts (chubby, playful).
    # Teens/adults get gender-specific body proportions (boy=sturdy, girl=graceful).
    # None of this injects text descriptions into the prompt — it just picks
    # which prompt FILE to load.
    detected_gender = gender if gender in ("boy", "girl") else "person"
    detected_age = age_range if age_range in ("toddler", "child", "teen", "adult") else "adult"

    # Build initial metadata
    meta = {
        "scene": "village",
        "subject": final_subject,
        "gender": detected_gender,
        "age_range": detected_age,
        "puzzle_size": puzzle_size,
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
        puzzle_size=int(puzzle_size.replace("pc", "")),
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

    ctx = {
        "job_id": job_id,
        "job": job,
        "step_data": step_data if step_data else None,
        "current_step": step,
        "total_cost": _total_cost(meta),
    }

    # Step 4: inject outfit choices so the wardrobe picker can render.
    if step == 4:
        from scene_prompts import get_scene
        scene_cfg = get_scene(meta.get("scene", "village"))
        ctx["outfit_choices"] = scene_cfg.get("outfit_choices", [])
        ctx["outfit_id"] = meta.get("outfit_id")

    return _render(request, STEP_TEMPLATES[step], ctx)


@app.get("/wizard/{job_id}/outfit-change")
async def wizard_change_outfit(job_id: str):
    """Clear current outfit choice so the wardrobe picker shows again."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    meta = _parse_metadata(job)
    meta.pop("outfit_id", None)
    meta.setdefault("steps", {}).pop("4", None)
    update_job(job_id, metadata=json.dumps(meta, default=str))

    return RedirectResponse(url=f"/wizard/{job_id}/step/4", status_code=303)


@app.post("/wizard/{job_id}/outfit")
async def wizard_set_outfit(
    job_id: str,
    outfit_id: str = Form(...),
):
    """Save the user's outfit choice to job metadata, then redirect to step 4."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    meta = _parse_metadata(job)
    meta["outfit_id"] = outfit_id
    # Reset step 4 so it re-runs with the new outfit choice.
    meta.setdefault("steps", {}).pop("4", None)
    update_job(job_id, metadata=json.dumps(meta, default=str))

    return RedirectResponse(url=f"/wizard/{job_id}/step/4", status_code=303)


@app.post("/wizard/{job_id}/step/{step}/regenerate")
async def wizard_step_regenerate(job_id: str, step: int):
    """Re-run step 3 or 4 with a fresh seed, clearing downstream results."""
    if step not in (3, 4):
        return HTMLResponse("Regenerate only supported for steps 3 and 4", status_code=400)

    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    meta = _parse_metadata(job)
    steps = meta.setdefault("steps", {})

    # Clear this step and all downstream steps
    for s in range(step, 6):
        steps.pop(str(s), None)

    # Use a new random seed so the re-run produces a different result
    meta["seed"] = random.randint(1, 999999)
    meta["current_step"] = step

    update_job(job_id, metadata=json.dumps(meta, default=str))
    return RedirectResponse(url=f"/wizard/{job_id}/step/{step}", status_code=303)


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

    return _render(request, "_wizard_poll.html", {
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
# Wizard: User picks favourite candidate → upscale
# ---------------------------------------------------------------------------

def _run_upscale(job_id: str, candidate_num: int):
    """Background task: upscale the user's chosen candidate, then export print files."""
    from pipeline_steps import step_upscale_final, step_export_for_print, save_manifest

    job = get_job(job_id)
    if not job:
        return

    meta = _parse_metadata(job)
    order_dir = Path("orders") / job_id
    step5 = meta.get("steps", {}).get("5", {})

    try:
        candidate_path = str(order_dir / f"candidate_{candidate_num}.png")
        result = step_upscale_final(candidate_path, str(order_dir))

        # Update step 5 with final result
        step5["final"] = result["final"]
        step5["final_size"] = result["final_size"]
        step5["cost"] = round(step5.get("cost", 0) + result["cost"], 3)
        step5["user_pick"] = candidate_num

        # Export print-ready files for Prodigi
        size_code = meta.get("puzzle_size", "252pc")
        export = step_export_for_print(result["final"], size_code, str(order_dir))
        step5["puzzle_surface"] = export["puzzle_surface"]
        step5["tin_lid"] = export["tin_lid"]
        step5["puzzle_surface_size"] = export["puzzle_surface_size"]
        step5["tin_lid_size"] = export["tin_lid_size"]
        step5["size_code"] = export["size_code"]

        step5["status"] = "complete"
        meta["steps"]["5"] = step5
        meta["total_cost"] = _total_cost(meta)

        save_manifest(str(order_dir), meta)
        update_job(job_id, status="completed", metadata=json.dumps(meta, default=str))

    except Exception as e:
        step5["status"] = "error"
        step5["error"] = str(e)
        meta["steps"]["5"] = step5
        update_job(job_id, status="error", error=str(e), metadata=json.dumps(meta, default=str))


@app.post("/wizard/{job_id}/pick-character")
async def wizard_pick_character(job_id: str, pick: int = Form(...)):
    """User picks their favourite character candidate."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    if pick not in (1, 2, 3):
        return HTMLResponse("Invalid selection", status_code=400)

    meta = _parse_metadata(job)
    step3 = meta.get("steps", {}).get("3", {})

    # Copy chosen candidate to character.png (used by step 4 costume)
    import shutil
    order_dir = Path("orders") / job_id
    src = order_dir / f"character_{pick}.png"
    dst = order_dir / "character.png"
    if src.exists():
        shutil.copy2(str(src), str(dst))
        # Whiten teeth on the chosen character before it feeds into costume
        from teeth_whitening import whiten_teeth
        whiten_teeth(str(dst))

    step3["character"] = str(dst)
    step3["user_pick"] = pick
    meta["steps"]["3"] = step3
    meta["current_step"] = 4
    update_job(job_id, metadata=json.dumps(meta, default=str))

    return RedirectResponse(url=f"/wizard/{job_id}/step/4", status_code=303)


@app.post("/wizard/{job_id}/pick")
async def wizard_pick(
    job_id: str,
    background_tasks: BackgroundTasks,
    pick: int = Form(...),
):
    """User picks their favourite candidate — trigger upscale."""
    job = get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    if pick not in (1, 2, 3):
        return HTMLResponse("Invalid selection", status_code=400)

    # Mark as upscaling
    meta = _parse_metadata(job)
    step5 = meta.get("steps", {}).get("5", {})
    step5["status"] = "upscaling"
    step5["user_pick"] = pick
    meta["steps"]["5"] = step5
    update_job(job_id, status="processing", metadata=json.dumps(meta, default=str))

    background_tasks.add_task(_run_upscale, job_id, pick)

    return RedirectResponse(url=f"/wizard/{job_id}/step/5", status_code=303)


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


@app.get("/wizard/{job_id}/download/puzzle-surface")
async def wizard_download_puzzle_surface(job_id: str):
    """Download the print-ready puzzle surface (exact Prodigi dimensions)."""
    path = Path("orders") / job_id / "puzzle_surface.jpg"
    if path.exists():
        return FileResponse(str(path), filename=f"{job_id}_puzzle_surface.jpg", media_type="image/jpeg")
    return HTMLResponse("File not available", status_code=404)


@app.get("/wizard/{job_id}/download/tin-lid")
async def wizard_download_tin_lid(job_id: str):
    """Download the print-ready tin lid image."""
    path = Path("orders") / job_id / "tin_lid.jpg"
    if path.exists():
        return FileResponse(str(path), filename=f"{job_id}_tin_lid.jpg", media_type="image/jpeg")
    return HTMLResponse("File not available", status_code=404)


# ---------------------------------------------------------------------------
# Wizard: Image serving
# ---------------------------------------------------------------------------

IMAGE_FILES = {
    "input_prepared": "input_prepared.png",
    "bg_removed": "bg_removed.jpg",
    "normalized": "normalized.png",
    "character": "character.png",
    "character_1": "character_1.png",
    "character_2": "character_2.png",
    "character_3": "character_3.png",
    "costumed": "costumed.png",
    "puzzle_surface": "puzzle_surface.jpg",
    "tin_lid": "tin_lid.jpg",
    "scene": "scene.png",
    "final": "final.png",
    "candidate_1": "candidate_1.png",
    "candidate_2": "candidate_2.png",
    "candidate_3": "candidate_3.png",
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

    return _render(request, "processing.html", {"job": job})


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
        return _render(request, "_status_complete.html", {"job": job})
    elif job["status"] == "error":
        return _render(request, "_status_error.html", {"job": job})
    else:
        return _render(request, "_status_processing.html", {"job": job})


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

    return _render(request, "preview.html", {"job": job, "feedback": feedback})


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
