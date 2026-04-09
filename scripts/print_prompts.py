"""Print all resolved prompts for a wizard job to terminal.

Usage:
    .venv/bin/python3 scripts/print_prompts.py <JOB_ID>

Useful for testing prompts against other models. Prints the exact prompts
used at each generation step — copy-paste into any model playground.
"""

import json
import sys
from pathlib import Path

# Add src and web to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "web"))

from jobs import get_job
from pipeline_steps import NORMALIZE_PROMPT
from scene_prompts import get_character_prompt, get_costume_prompt, get_scene


def print_prompts(job_id: str):
    """Print all prompts for the given job ID."""
    job = get_job(job_id)
    if not job:
        print(f"Job '{job_id}' not found.")
        sys.exit(1)

    raw_meta = job.get("metadata", "{}")
    meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta

    scene_id = meta.get("scene", "village")
    subject = meta.get("subject", "the person in the input image")
    gender = meta.get("gender", "person")
    outfit_id = meta.get("outfit_id")
    steps = meta.get("steps", {})

    print(f"\n{'=' * 60}")
    print(f"PROMPTS FOR JOB: {job_id}")
    print(f"{'=' * 60}")
    print(f"Scene:   {scene_id}")
    print(f"Subject: {subject}")
    print(f"Gender:  {gender}")
    print(f"Outfit:  {outfit_id or '(none selected)'}")
    print(f"Status:  {job.get('status', 'unknown')}")
    print(f"Cost:    ${meta.get('total_cost', 0):.3f}")

    # Step 2b — Portrait normalisation
    print(f"\n{'-' * 60}")
    print("STEP 2b: PORTRAIT NORMALISATION  (flux-kontext-max, $0.08)")
    print(f"{'-' * 60}")
    print(NORMALIZE_PROMPT)

    # Step 3 — Character generation
    print(f"\n{'-' * 60}")
    print("STEP 3: CHARACTER GENERATION  (flux-kontext-max, $0.08)")
    print(f"{'-' * 60}")
    step3 = steps.get("3", {})
    # Use stored prompt if present — exact prompt used at generation time
    char_prompt = step3.get("prompt") or get_character_prompt(scene_id, subject, gender)
    print(char_prompt)

    # Step 4 — Costume
    print(f"\n{'-' * 60}")
    outfit_label = f"outfit: {outfit_id}" if outfit_id else "no outfit selected"
    print(f"STEP 4: COSTUME  (flux-kontext-max, $0.08, {outfit_label})")
    print(f"{'-' * 60}")
    costume_prompt = get_costume_prompt(scene_id, subject, outfit_id)
    print(costume_prompt)

    # Step 5a — Scene generation
    print(f"\n{'-' * 60}")
    print("STEP 5a: SCENE GENERATION  (flux-2-pro, ~$0.08)")
    print(f"{'-' * 60}")
    scene_cfg = get_scene(scene_id)
    print(scene_cfg["scene_prompt"])

    # Step 5b — Compositing
    print(f"\n{'-' * 60}")
    print("STEP 5b: COMPOSITING METHOD E  (flux-kontext-max, $0.08 × 3 seeds)")
    print(f"{'-' * 60}")
    print(scene_cfg["composite_E_prompt"])

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python3 scripts/print_prompts.py <JOB_ID>")
        print("\nRecent jobs can be found by running the web app and checking the dashboard.")
        sys.exit(1)
    print_prompts(sys.argv[1])
