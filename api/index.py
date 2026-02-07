"""Vercel entrypoint — re-exports the FastAPI app."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from web.app import app
