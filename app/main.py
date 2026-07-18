"""FastAPI application for GlassBox Sentinel."""

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from config.settings import Settings, settings
from app.entropy import EntropyConfig
from app.models import (
    RunState, RunStatus, AgentStepStatus, CreateRunRequest, OverrideRequest,
    EntropyBreakdown, SaveState, DecisionTree,
    VibeToolEventRequest,
)
from app.run_manager import RunManager
from app.compressor import Compressor
from app.worker import Worker
from app.scenarios import get_available_scenarios, load_scenario
from app.weave_api import execute_weave_drill

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create entropy config from settings
entropy_config = EntropyConfig(
    window_w=settings.window_w,
    consecutive_error_n=settings.consecutive_error_n,
    no_progress_p=settings.no_progress_p,
    max_steps=settings.max_steps,
    threshold=settings.threshold,
    weights=settings.weights,
)

# Create run manager and compressor
run_manager = RunManager(entropy_config)
compressor = Compressor(settings)

# Store active workers
active_workers: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    logger.info("Starting GlassBox Sentinel...")
    yield
    logger.info("Shutting down GlassBox Sentinel...")
    # Clean up workers
    for worker in active_workers.values():
        worker.stop()
    active_workers.clear()


app = FastAPI(
    title="GlassBox Sentinel",
    description="Evidence-first runtime safety control plane for coding agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


def _require_vibe_token(token: str | None) -> None:
    """Require the per-install secret used by the local Vibe hook adapter."""
    configured = settings.vibe_hook_token
    if not configured:
        raise HTTPException(status_code=503, detail="Vibe hook token is not configured")
    if not token or not secrets.compare_digest(token, configured):
        raise HTTPException(status_code=401, detail="Invalid Vibe hook token")


def _normalize_vibe_status(value: str) -> AgentStepStatus:
    """Map the hook adapter statuses to the existing timeline statuses."""
    if value in AgentStepStatus._value2member_map_:
        return AgentStepStatus(value)
    if value in {"failure", "failed", "cancelled"}:
        return AgentStepStatus.error
    return AgentStepStatus.noop if value in {"pending", "unknown"} else AgentStepStatus.ok


async def _publish_vibe_brake(run: RunState) -> None:
    """Publish the same brake artifacts that fixture workers expose over SSE."""
    save_state, decision_tree = await compressor.compress(run.run_id, run.steps, run.goal)
    run.meta["compress_source"] = save_state.compress_source
    await run_manager.update_run(run.run_id, {
        "save_state": save_state,
        "decision_tree": decision_tree,
        "voice_alert_text": "Agent is stuck in a loop. Human override required.",
    })
    await run_manager.emit_event(run.run_id, "braked", {
        "run_id": run.run_id,
        "reason": "vibe_entropy",
        "entropy": run.entropy.model_dump() if run.entropy else {},
    })
    await run_manager.emit_event(run.run_id, "voice", {
        "run_id": run.run_id,
        "text": "Agent is stuck in a loop. Human override required.",
    })
    await run_manager.emit_event(run.run_id, "save_state", save_state.model_dump())
    await run_manager.emit_event(run.run_id, "tree", decision_tree.model_dump())


# ==================== Health ====================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ==================== Scenarios ====================

@app.get("/api/scenarios")
async def list_scenarios():
    """List available scenarios."""
    scenarios = get_available_scenarios()
    return {"scenarios": scenarios}


# ==================== Runs ====================

@app.post("/api/runs")
async def create_run(request: CreateRunRequest):
    """Create a new run."""
    run = await run_manager.create_run(request.scenario_id)
    return run


@app.get("/api/runs")
async def get_runs():
    """Get all runs."""
    runs = await run_manager.get_runs()
    return {"runs": [r.model_dump() for r in runs]}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific run by ID."""
    run = await run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/api/runs/{run_id}/start")
async def start_run(run_id: str):
    """Start a run."""
    run = await run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != RunStatus.idle:
        raise HTTPException(
            status_code=409,
            detail=f"Run is not idle (current: {run.status})"
        )
    
    # Start the run
    started = await run_manager.start_run(run_id)
    if not started:
        raise HTTPException(status_code=409, detail="Could not start run")
    
    if run.meta.get("worker_mode") == "immunity_campaign":
        asyncio.create_task(run_manager.run_immunity_campaign(run_id))
        return {"message": "Sentinel Immunity campaign started", "run_id": run_id}

    # Create and start worker
    worker = Worker(
        run_id=run_id,
        scenario_id=run.scenario_id,
        run_manager=run_manager,
        entropy_config=entropy_config,
        compressor=compressor,
        step_delay_ms=(settings.step_delay_ms_min, settings.step_delay_ms_max)
    )
    active_workers[run_id] = worker
    
    # Start worker in background
    asyncio.create_task(worker.run())
    
    return {"message": "Run started", "run_id": run_id}


@app.post("/api/runs/{run_id}/override")
async def add_override(run_id: str, request: OverrideRequest):
    """Select an evidence-backed fixture recovery, or control a live Vibe run."""
    run = await run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.braked:
        raise HTTPException(status_code=409, detail=f"Run is not braked (current: {run.status})")

    # Live Vibe runs intentionally retain a free-form instruction channel.
    if run.meta.get("source") == "vibe":
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Vibe override text cannot be empty")
        accepted = await run_manager.add_override(run_id, request.text)
        if not accepted:
            raise HTTPException(status_code=409, detail="Could not accept Vibe override")
        return {"message": "Vibe override accepted", "run_id": run_id}

    selected, reason = await run_manager.select_fixture_recovery(
        run_id, request.choice_id, request.rationale
    )
    if not selected:
        raise HTTPException(
            status_code=422,
            detail="Choose an evidence-backed recovery option before authorizing recovery.",
        )
    updated = await run_manager.get_run(run_id)
    return {"message": "Recovery option selected", "run_id": run_id, "run": updated}


@app.post("/api/runs/{run_id}/override/authorize")
async def authorize_override(run_id: str):
    """Explicitly authorize the previously selected fixture recovery."""
    run = await run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.braked:
        raise HTTPException(status_code=409, detail=f"Run is not braked (current: {run.status})")
    if run.meta.get("source") == "vibe":
        raise HTTPException(status_code=409, detail="Vibe runs use the live override instruction control")

    worker = active_workers.get(run_id)
    if not worker:
        raise HTTPException(status_code=409, detail="No active worker for this run")
    authorized, reason = await run_manager.authorize_fixture_recovery(run_id)
    if not authorized:
        if reason == "already_authorized":
            raise HTTPException(status_code=409, detail="Recovery has already been authorized")
        raise HTTPException(status_code=422, detail="Select an evidence-backed recovery option before authorizing it")
    worker.resume()
    updated = await run_manager.get_run(run_id)
    return {"message": "Recovery authorized", "run_id": run_id, "run": updated}


# ==================== Vibe Hooks ====================

@app.post("/api/v1/vibe/events")
async def ingest_vibe_event(
    request: VibeToolEventRequest,
    x_glassbox_token: str | None = Header(default=None),
):
    """Ingest a completed Vibe tool call from the project-local hook adapter."""
    _require_vibe_token(x_glassbox_token)
    is_pre = request.phase == "pre_tool" or request.event_type == "tool.pre"
    is_post = request.phase == "post_tool" or request.event_type in {"post_tool", "tool.post"}
    if is_pre:
        run, created = await run_manager.create_vibe_run(request.session_id, request.goal)
        return {
            "run_id": run.run_id,
            "run": run.model_dump(),
            "created": created,
            "deduplicated": False,
            "braked": run.status == RunStatus.braked,
        }
    if not is_post:
        raise HTTPException(status_code=400, detail="Vibe event must be tool.pre or tool.post")

    run, created, deduplicated, braked = await run_manager.ingest_vibe_tool_event(
        event_id=request.event_id,
        session_id=request.session_id,
        goal=request.goal,
        tool_name=request.tool_name,
        input_summary=request.input_summary or "",
        output_summary=request.output_summary or "",
        status=_normalize_vibe_status(request.status),
        error_signature=request.error_signature,
        files_touched=request.files_touched,
        timestamp=request.timestamp,
    )
    if not deduplicated and run.status not in (RunStatus.running, RunStatus.running_resume, RunStatus.braked):
        raise HTTPException(status_code=409, detail=f"Vibe run is not accepting events (current: {run.status.value})")
    if braked:
        await _publish_vibe_brake(run)
    return {
        "run_id": run.run_id,
        "run": run.model_dump(),
        "created": created,
        "deduplicated": deduplicated,
        "braked": braked,
    }


@app.get("/api/v1/vibe/control")
async def get_vibe_control(
    session_id: str,
    x_glassbox_token: str | None = Header(default=None),
):
    """Return allow, wait, override_instruction, or abort for Vibe pre-tool hooks."""
    _require_vibe_token(x_glassbox_token)
    return await run_manager.get_vibe_control(session_id)


@app.post("/api/v1/vibe/sessions/{session_id}/abort")
async def abort_vibe_session(
    session_id: str,
    x_glassbox_token: str | None = Header(default=None),
):
    _require_vibe_token(x_glassbox_token)
    run = await run_manager.abort_vibe_run(session_id)
    if not run:
        raise HTTPException(status_code=404, detail="Vibe session not found")
    return {"message": "Vibe run aborted", "run_id": run.run_id}



@app.get("/api/v1/runs/{run_id}/control")
async def get_vibe_run_control(
    run_id: str,
    session_id: str,
    tool_call_id: str | None = None,
    x_glassbox_token: str | None = Header(default=None),
):
    """Compatibility control contract for the project-local Vibe hook adapter."""
    _require_vibe_token(x_glassbox_token)
    run = await run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.meta.get("source") != "vibe" or run.meta.get("vibe_session_id") != session_id:
        raise HTTPException(status_code=409, detail="Vibe session does not match run")
    decision = await run_manager.get_vibe_control(session_id)
    if decision.get("action") == "override_instruction":
        return {
            "action": "override",
            "run_id": decision["run_id"],
            "instruction": decision["instruction"],
        }
    return decision

# ==================== SSE Stream ====================

@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    """Stream events for a run using Server-Sent Events."""
    run = await run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    async def event_generator():
        queue = await run_manager.subscribe(run_id)
        try:
            while True:
                event_type, event_data = await queue.get()
                yield {
                    "event": event_type,
                    "data": event_data,
                }
        except asyncio.CancelledError:
            await run_manager.unsubscribe(run_id, queue)
            raise
    
    return EventSourceResponse(event_generator())


# ==================== Demo Endpoints ====================

@app.post("/api/demo/load-golden")
async def load_golden_braked_run():
    """Load a golden braked run for demo purposes."""
    import json
    from pathlib import Path
    
    golden_file = Path("fixtures/golden_braked_run.json")
    if not golden_file.exists():
        raise HTTPException(status_code=404, detail="Golden fixture not found")
    
    with open(golden_file, 'r') as f:
        data = json.load(f)
    
    run = RunState(**data)
    run_manager.runs[run.run_id] = run
    
    return {"message": "Golden run loaded", "run_id": run.run_id}


@app.get("/")
async def root():
    """Serve the public Vibe Weave product site."""
    from fastapi.responses import FileResponse

    return FileResponse(
        "static/weave.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/api/v1/weave/drill")
async def run_public_weave_drill(decision: str = "admin_only"):
    """Run the public credential-free Vibe Weave proof."""
    return await execute_weave_drill(decision)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level,
    )
