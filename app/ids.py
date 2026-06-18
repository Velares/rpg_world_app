from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    """Return a compact, readable ID suitable for saved relationship references."""
    return f"{prefix}-{uuid4().hex[:12]}"
