"""
SQLite-based job tracking for the web interface.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Use absolute path relative to this file so it works regardless of CWD
DB_PATH = Path(__file__).parent / "puzzle_photos_feedback.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the jobs table if it doesn't exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            photo_path TEXT,
            style TEXT,
            subject TEXT,
            backend TEXT DEFAULT 'flux_kontext',
            puzzle_size INTEGER DEFAULT 1000,
            preview_path TEXT,
            print_ready_path TEXT,
            quality_score REAL,
            error TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            rating INTEGER,
            comment TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_job(
    job_id: str,
    photo_path: str,
    style: str,
    subject: str,
    backend: str = "flux_kontext",
    puzzle_size: int = 1000,
    metadata: str = "{}",
) -> Dict:
    """Create a new job."""
    now = datetime.now().isoformat()
    conn = _get_connection()
    conn.execute(
        """INSERT INTO jobs (id, photo_path, style, subject, backend, puzzle_size, metadata, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (job_id, photo_path, style, subject, backend, puzzle_size, metadata, now, now),
    )
    conn.commit()
    conn.close()
    return get_job(job_id)


def get_job(job_id: str) -> Optional[Dict]:
    """Get a job by ID."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def update_job(job_id: str, **kwargs) -> Optional[Dict]:
    """Update job fields."""
    if not kwargs:
        return get_job(job_id)

    kwargs["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]

    conn = _get_connection()
    conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_job(job_id)


def save_feedback(job_id: str, rating: int, comment: str = "") -> Dict:
    """Save feedback for a job."""
    now = datetime.now().isoformat()
    conn = _get_connection()
    conn.execute(
        "INSERT INTO feedback (job_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
        (job_id, rating, comment, now),
    )
    conn.commit()
    conn.close()
    return {"job_id": job_id, "rating": rating, "comment": comment, "created_at": now}


def get_feedback(job_id: str) -> Optional[Dict]:
    """Get the most recent feedback for a job."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM feedback WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
        (job_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def list_jobs(limit: int = 50) -> List[Dict]:
    """List recent jobs."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize DB on import
init_db()
