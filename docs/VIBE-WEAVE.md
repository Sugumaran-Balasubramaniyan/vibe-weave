# Vibe Weave

Vibe Weave is a project-local coordination companion for Mistral Vibe. It makes the semantic contract between delegated roles explicit before managed code edits begin.

## What it adds to Vibe

1. Roles propose compact `ChangeContract` records: file scope, assumptions, public contract, and proof.
2. The engine finds contradictory decisions and ranks them by impact.
3. It asks one decision question, persists the resulting `DecisionContract`, and unblocks work.
4. The project-local `pre_tool` hook blocks managed edits while a recorded conflict remains unresolved.

This is deliberately a coordination layer, not another agent loop: Vibe continues to choose and run its subagents, while Weave supplies shared definition-of-done and an auditable convergence point.

## Credential-free demo

From the repository root:

```bash
PYTHONPATH=. .venv/bin/python -m vibe_weave drill --output /tmp/vibe-weave-proof
sed -n '1,160p' /tmp/vibe-weave-proof/weave-report.md
```

The deterministic invoice-export drill simulates three roles in real isolated Git worktrees. The frontend proposes `authenticated_user`; backend and tests propose `admin_only`. Weave raises **“Who may export invoices?”**, resolves the selected answer, and emits JSON plus Markdown evidence.

## Mistral Vibe integration

The local assets are intentionally checked into the project:

- `.vibe/agents/weave-coordinator.toml` exposes a Vibe coordinator persona.
- `.vibe/skills/vibe-weave/SKILL.md` instructs delegated roles to submit contracts and prove their work.
- `.vibe/hooks.toml` runs `python3 -m vibe_weave guard` before managed write tools.

No decision state means the hook is transparent. An unresolved conflict state blocks `write_file`, `search_replace`, and `bash`; a resolved decision lets Vibe continue.

## Demo narration

“Vibe can delegate tasks. Vibe Weave makes delegations converge on one shared meaning before implementation. Here, three agents disagree on who may export invoices. Rather than producing a plausible but incoherent patch set, Weave asks the single decision that changes every downstream implementation, records it, and proves the work happened in isolated worktrees.”
