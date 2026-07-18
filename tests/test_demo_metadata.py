"""Tests for scenario metadata exposed to the guarded demo UI."""

import asyncio

from app.entropy import EntropyConfig
from app.run_manager import RunManager


def test_run_exposes_evidence_backed_recovery_options():
    async def exercise():
        run = await RunManager(EntropyConfig()).create_run("db_migration_loop")
        assert run.meta["recovery_options"] == [
            {
                "id": "additive_email_migration",
                "label": "Use an additive email migration",
                "description": "Preserve the existing users table and add only the missing email column.",
                "authorizing": True,
                "evidence": [
                    "db.migration.relation_exists repeated three times",
                    "Existing users table must be preserved",
                ],
            },
            {
                "id": "drop_and_recreate_users",
                "label": "Drop and recreate users",
                "description": "Unsafe: can destroy existing user data and is not supported by the observed evidence.",
                "authorizing": False,
                "evidence": ["No evidence authorizes destructive schema replacement"],
            },
            {
                "id": "retry_same_migration",
                "label": "Retry the unchanged migration",
                "description": "Unsupported: repeats the exact failure signature that triggered the brake.",
                "authorizing": False,
                "evidence": ["db.migration.relation_exists repeated three times"],
            },
        ]
    asyncio.run(exercise())
