"""Credential-free authorization-scope drill used in the hackathon demo."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from .contracts import ChangeContract, WeaveState
from .engine import detect_conflicts, resolve, save_state


def sample_contracts() -> list[ChangeContract]:
    return [
        ChangeContract("frontend", "frontend", "Expose invoice export", ("ui/invoice_export.ts",), {"invoice_export.authorization": "authenticated_user"}, ("invoice export UI",), ("export button hides for non-admin",)),
        ChangeContract("backend", "backend", "Add export endpoint", ("api/invoices.py",), {"invoice_export.authorization": "admin_only"}, ("GET /invoices/{id}/export",), ("non-admin request returns 403",)),
        ChangeContract("tests", "test", "Protect export behavior", ("tests/test_invoice_export.py",), {"invoice_export.authorization": "admin_only"}, ("invoice export regression",), ("admin export returns 200", "non-admin request returns 403")),
    ]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def run_drill(output_dir: Path, answer: str = "admin_only") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    contracts = sample_contracts()
    conflicts = detect_conflicts(contracts)
    conflict = conflicts[0]
    resolved_contracts, decision = resolve(conflict, answer, contracts)
    conflict = replace(conflict, status="resolved")
    state = WeaveState(contracts=resolved_contracts, conflicts=[conflict], decisions=[decision])
    save_state(state, output_dir / "weave-state.json")

    fixture_root = Path(tempfile.mkdtemp(prefix="vibe-weave-drill-"))
    repo = fixture_root / "invoice-export"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.email", "weave@example.invalid")
    _git(repo, "config", "user.name", "Vibe Weave")
    (repo / "README.md").write_text("# Invoice export fixture\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "seed fixture")
    worktrees: dict[str, str] = {}
    for contract in resolved_contracts:
        worktree = fixture_root / f"weave-{contract.id}"
        _git(repo, "worktree", "add", "--detach", str(worktree), "HEAD")
        worktrees[contract.id] = str(worktree)
    verification = {
        "authorization": answer == "admin_only",
        "all_contracts_resolved": all(contract.status == "resolved" for contract in resolved_contracts),
        "worktrees_created": all((Path(path) / ".git").exists() for path in worktrees.values()),
    }
    verification["passed"] = all(verification.values())
    report = {
        "product": "Vibe Weave", "fixture": "deterministic authorization-scope drill",
        "question": conflict.question, "options": conflict.options, "answer": answer,
        "decision": decision.to_dict(), "worktrees": worktrees, "verification": verification,
    }
    (output_dir / "weave-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "weave-report.md").write_text(
        f"# Vibe Weave proof\n\n## Question\n\n{conflict.question}\n\n"
        f"**Resolved:** `{answer}`\n\n## Verification\n\n"
        f"- Isolated worktrees: {'PASS' if verification['worktrees_created'] else 'FAIL'}\n"
        f"- Contracts converged: {'PASS' if verification['all_contracts_resolved'] else 'FAIL'}\n"
        f"- Authorization policy: {'PASS' if verification['authorization'] else 'FAIL'}\n",
        encoding="utf-8",
    )
    return report
