"""Cancellation behavior for an authorized active worker."""

import asyncio

from app.compressor import Compressor
from app.entropy import EntropyConfig
from app.models import RunStatus
from app.run_manager import RunManager
from app.worker import Worker
from config.settings import settings


def test_stop_during_authorized_recovery_does_not_report_completed():
    async def exercise():
        entropy_config = EntropyConfig()
        run_manager = RunManager(entropy_config)
        run = await run_manager.create_run("db_migration_loop")
        await run_manager.start_run(run.run_id)
        worker = Worker(run.run_id, run.scenario_id, run_manager, entropy_config, Compressor(settings), (1, 1))
        worker_task = asyncio.create_task(worker.run())
        for _ in range(200):
            if (await run_manager.get_run(run.run_id)).status == RunStatus.braked:
                break
            await asyncio.sleep(0.01)
        assert await run_manager.authorize_fixture_recovery(run.run_id) == (False, "no_authorizing_selection")
        assert await run_manager.select_fixture_recovery(run.run_id, "additive_email_migration", "Stop after authorization") == (True, "selected")
        assert await run_manager.authorize_fixture_recovery(run.run_id) == (True, "authorized")
        worker.resume()
        for _ in range(200):
            if (await run_manager.get_run(run.run_id)).status == RunStatus.running_resume:
                break
            await asyncio.sleep(0.01)
        worker.stop()
        await worker_task
        stopped_run = await run_manager.get_run(run.run_id)
        assert stopped_run.status == RunStatus.failed
        assert stopped_run.meta["error"] == "Worker stopped"
    asyncio.run(exercise())
