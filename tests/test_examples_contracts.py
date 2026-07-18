"""Keep the beginner-facing example contracts readable by the real parser."""

import json
from pathlib import Path

from vibe_weave.contracts import ChangeContract
from vibe_weave.engine import detect_conflicts


EXAMPLE_ROOT = Path("examples")


def test_every_example_contract_file_is_valid_and_exposes_a_real_conflict():
    contract_files = sorted(EXAMPLE_ROOT.glob("*/contracts.json"))

    assert len(contract_files) >= 3
    for contract_file in contract_files:
        payload = json.loads(contract_file.read_text(encoding="utf-8"))
        contracts = [ChangeContract.from_dict(item) for item in payload]
        assert len(contracts) >= 2
        assert detect_conflicts(contracts), f"{contract_file} should teach a disagreement"
