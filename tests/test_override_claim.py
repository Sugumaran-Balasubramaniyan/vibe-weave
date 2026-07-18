"""Live Vibe override ownership tests."""

import asyncio

from app.entropy import EntropyConfig
from app.models import RunStatus
from app.run_manager import RunManager


def test_only_the_first_vibe_override_is_accepted_for_a_braked_run():
    async def exercise():
        run_manager = RunManager(EntropyConfig())
        run, _ = await run_manager.create_vibe_run("session-1", "Repair migration")
        run.status = RunStatus.braked
        assert await run_manager.add_override(run.run_id, "Inspect the current migration")
        assert not await run_manager.add_override(run.run_id, "Drop and recreate the table")
        updated_run = await run_manager.get_run(run.run_id)
        assert [override["text"] for override in updated_run.overrides] == ["Inspect the current migration"]
    asyncio.run(exercise())
