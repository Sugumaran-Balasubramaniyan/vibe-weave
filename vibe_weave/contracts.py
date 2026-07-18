"""Versioned, inspectable artifacts exchanged by Vibe Weave participants."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChangeContract:
    id: str
    role: str
    goal: str
    files: tuple[str, ...]
    decisions: dict[str, str]
    public_contracts: tuple[str, ...]
    proofs: tuple[str, ...]
    status: str = "proposed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChangeContract":
        required = ("id", "role", "goal", "files", "decisions", "public_contracts", "proofs")
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"change contract missing: {', '.join(missing)}")
        return cls(
            id=str(data["id"]), role=str(data["role"]), goal=str(data["goal"]),
            files=tuple(map(str, data["files"])),
            decisions={str(key): str(value) for key, value in data["decisions"].items()},
            public_contracts=tuple(map(str, data["public_contracts"])),
            proofs=tuple(map(str, data["proofs"])), status=str(data.get("status", "proposed")),
        )


@dataclass(frozen=True)
class Conflict:
    id: str
    decision_key: str
    options: dict[str, tuple[str, ...]]
    affected_contracts: tuple[str, ...]
    impact_score: int
    question: str
    status: str = "unresolved"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionContract:
    id: str
    decision_key: str
    answer: str
    affected_contracts: tuple[str, ...]
    required_proofs: tuple[str, ...]
    rationale: str
    status: str = "resolved"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeaveState:
    contracts: list[ChangeContract] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    decisions: list[DecisionContract] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contracts": [contract.to_dict() for contract in self.contracts],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "decisions": [decision.to_dict() for decision in self.decisions],
        }
