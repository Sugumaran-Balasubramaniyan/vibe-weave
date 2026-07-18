from vibe_weave.contracts import WeaveState
from vibe_weave.drill import run_drill, sample_contracts
from vibe_weave.engine import detect_conflicts, guard, load_state, resolve


def test_authorization_conflict_is_ranked_and_resolved():
    contracts = sample_contracts()
    conflicts = detect_conflicts(contracts)

    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.decision_key == "invoice_export.authorization"
    assert conflict.question == "Who may export invoices?"
    assert conflict.impact_score > 0

    resolved_contracts, decision = resolve(conflict, "admin_only", contracts)

    assert decision.answer == "admin_only"
    assert all(contract.decisions[conflict.decision_key] == "admin_only" for contract in resolved_contracts)
    assert all(contract.status == "resolved" for contract in resolved_contracts)


def test_guard_blocks_managed_edits_while_a_conflict_is_unresolved():
    state = WeaveState(contracts=sample_contracts(), conflicts=detect_conflicts(sample_contracts()))

    blocked = guard({"tool_name": "write_file"}, state)
    allowed = guard({"tool_name": "read_file"}, state)

    assert blocked["decision"] == "deny"
    assert "Who may export invoices?" in blocked["reason"]
    assert allowed["decision"] == "allow"


def test_drill_creates_state_report_and_real_worktrees(tmp_path):
    result = run_drill(tmp_path, answer="admin_only")
    state = load_state(tmp_path / "weave-state.json")

    assert result["verification"]["passed"] is True
    assert (tmp_path / "weave-report.json").exists()
    assert (tmp_path / "weave-report.md").exists()
    assert state.conflicts[0].status == "resolved"
    assert result["verification"]["worktrees_created"] is True
