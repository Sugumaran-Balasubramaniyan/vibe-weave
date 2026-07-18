"""HTTP adapter for the public, deterministic Vibe Weave proof."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import HTTPException

from vibe_weave.drill import run_drill


async def execute_weave_drill(decision: str) -> dict:
    """Run only the credential-free fixture in a disposable temporary directory."""
    if decision not in {"admin_only", "authenticated_user"}:
        raise HTTPException(status_code=422, detail="Unsupported authorization decision")
    output_dir = Path(tempfile.mkdtemp(prefix="vibe-weave-web-")) / "proof"
    return await asyncio.to_thread(run_drill, output_dir, decision)
