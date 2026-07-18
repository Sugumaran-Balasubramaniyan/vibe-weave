"""Deterministic semantic coordination engine for Vibe Weave v1."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .contracts import ChangeContract, Conflict, DecisionContract, WeaveState


DECISION_QUESTIONS = {
    "invoice_export.authorization": "Who may export invoices?",
}


def detect_conflicts(contracts: Iterable[ChangeContract]) -> list[Conflict]:
    contracts = list(contracts)
    values: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for contract in contracts:
        for key, value in contract.decisions.items():
            values[key][value].append(contract.id)
    conflicts: list[Conflict] = []
    for key, options in values.items():
        if len(options) < 2:
            continue
        affected = tuple(sorted({identifier for ids in options.values() for identifier in ids}))
        impact = len(affected) * 10 + sum(
            len(contract.public_contracts) for contract in contracts if contract.id in affected
        )
        conflicts.append(Conflict(
            id=f"conflict-{key.replace('.', '-')}", decision_key=key,
            options={value: tuple(sorted(ids)) for value, ids in sorted(options.items())},
            affected_contracts=affected, impact_score=impact,
            question=DECISION_QUESTIONS.get(key, f"Resolve semantic decision: {key}"),
        ))
    return sorted(conflicts, key=lambda conflict: (-conflict.impact_score, conflict.id))


def resolve(conflict: Conflict, answer: str, contracts: Iterable[ChangeContract]) -> tuple[list[ChangeContract], DecisionContract]:
    if answer not in conflict.options:
        raise ValueError(f"answer {answer!r} is not one of: {', '.join(conflict.options)}")
    updated: list[ChangeContract] = []
    for contract in contracts:
        if contract.id not in conflict.affected_contracts:
            updated.append(contract)
            continue
        decisions = dict(contract.decisions)
        decisions[conflict.decision_key] = answer
        updated.append(ChangeContract(
            id=contract.id, role=contract.role, goal=contract.goal, files=contract.files,
            decisions=decisions, public_contracts=contract.public_contracts,
            proofs=contract.proofs, status="resolved",
        ))
    proofs = tuple(sorted({proof for contract in updated if contract.id in conflict.affected_contracts for proof in contract.proofs}))
    decision = DecisionContract(
        id=f"decision-{conflict.decision_key.replace('.', '-')}", decision_key=conflict.decision_key,
        answer=answer, affected_contracts=conflict.affected_contracts, required_proofs=proofs,
        rationale=f"User selected {answer} for {conflict.question}",
    )
    return updated, decision


def save_state(state: WeaveState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_state(path: Path) -> WeaveState:
    data = json.loads(path.read_text(encoding="utf-8"))
    return WeaveState(
        contracts=[ChangeContract.from_dict(item) for item in data.get("contracts", [])],
        conflicts=[Conflict(**item) for item in data.get("conflicts", [])],
        decisions=[DecisionContract(**item) for item in data.get("decisions", [])],
    )


def guard(invocation: dict, state: WeaveState) -> dict:
    unresolved = [conflict for conflict in state.conflicts if conflict.status == "unresolved"]
    tool_name = invocation.get("tool_name", "")
    if unresolved and tool_name in {"write_file", "search_replace", "bash"}:
        return {"decision": "deny", "reason": f"Vibe Weave blocks managed edits until {unresolved[0].question}"}
    return {"decision": "allow"}
