from typing import Dict

from backends.base import BaseBackend
from backends.flux_kontext import FluxKontextBackend

_BACKENDS: Dict[str, type] = {
    "flux_kontext": FluxKontextBackend,
}


def get_backend(name: str) -> BaseBackend:
    """Get a backend instance by name.

    Args:
        name: Backend identifier (e.g. flux_kontext).

    Returns:
        Instantiated backend.

    Raises:
        ValueError: If backend name is unknown.
    """
    key = name.lower()
    if key not in _BACKENDS:
        available = ", ".join(sorted(_BACKENDS.keys()))
        raise ValueError(f"Unknown backend '{name}'. Available: {available}")
    return _BACKENDS[key]()


def list_backends() -> Dict[str, Dict]:
    """Return capabilities of all registered backends."""
    return {name: cls().get_capabilities() for name, cls in _BACKENDS.items()}
