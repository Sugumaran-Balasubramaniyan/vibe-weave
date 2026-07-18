"""Terminal entry point for Vibe Weave."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .drill import run_drill
from .engine import guard, load_state


def main() -> int:
    parser = argparse.ArgumentParser(prog="weave", description="Semantic coordination for Mistral Vibe subagents")
    subcommands = parser.add_subparsers(dest="command", required=True)
    drill = subcommands.add_parser("drill", help="run the deterministic authorization conflict proof")
    drill.add_argument("--output", type=Path, default=Path(".vibe/weave"))
    drill.add_argument("--decision", default="admin_only", choices=("admin_only", "authenticated_user"))
    hook = subcommands.add_parser("guard", help="Vibe pre_tool hook adapter")
    hook.add_argument("--state", type=Path, default=Path(".vibe/weave/weave-state.json"))
    args = parser.parse_args()
    if args.command == "drill":
        report = run_drill(args.output, args.decision)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verification"]["passed"] else 1
    invocation = json.load(sys.stdin)
    state = load_state(args.state) if args.state.exists() else WeaveState()
    print(json.dumps(guard(invocation, state)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
