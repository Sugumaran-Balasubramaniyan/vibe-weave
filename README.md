# Vibe Weave

> Semantic coordination for Mistral Vibe subagents — agree on what done means before parallel agents edit code.

[Live demo](https://www.glassbox.sugumaran-balasubramaniyan.com) · [46-second narrated product pitch](https://www.glassbox.sugumaran-balasubramaniyan.com/static/vibe-weave-explainer.mp4?v=weave-v2)

## The problem

A frontend agent, backend agent, and test agent can each write sensible code while silently disagreeing about one product decision. The resulting pull request looks complete, but its behavior is incoherent.

Vibe Weave catches that disagreement before managed edits begin.

```
agent plans  ->  Change Contracts  ->  conflict found
                                      |
                                      v
                            one clear question
                                      |
                                      v
                         Decision Contract + proofs
                                      |
                                      v
                    isolated worktrees, aligned result
```

## The demo in one minute

The included fixture asks three agents to implement invoice export:

| Role | Assumption |
| --- | --- |
| Frontend | Any signed-in user may export |
| Backend | Only admins may export |
| Tests | Only admins may export |

Weave detects the mismatch and asks: **Who may export invoices?**

Choose `admin_only` and Weave writes a Decision Contract, creates real disposable Git worktrees, and verifies that every role converged. Choosing `authenticated_user` deliberately fails the safety proof so the negative path is visible.

## What is new

Mistral Vibe can already delegate and run agents. Vibe Weave adds the missing shared semantic checkpoint:

- **Change Contract** — what a role intends to edit, assumes, exposes, and will prove.
- **Conflict ranking** — find incompatible meanings and ask the highest-impact question first.
- **Decision Contract** — persist one answer that all affected roles share.
- **Pre-tool guard** — hold managed write tools while an unresolved conflict exists.
- **Worktree proof** — use isolated Git worktrees and explicit evidence to show convergence.

Vibe runs the agents. **Vibe Weave makes them agree.**

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python -m vibe_weave drill --output /tmp/vibe-weave-proof
sed -n "1,160p" /tmp/vibe-weave-proof/weave-report.md
```

Run the public product site locally:

```bash
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`, choose **Live proof**, select a decision, and press **Resolve & prove**.

## Mistral Vibe integration

Project-local integration assets are already included:

```text
.vibe/agents/weave-coordinator.toml
.vibe/skills/vibe-weave/SKILL.md
.vibe/hooks.toml
```

The `pre_tool` hook runs `python3 -m vibe_weave guard`. It is transparent without unresolved state and blocks managed write tools only while a known semantic conflict remains open.

## Verify

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/pytest -p no:cacheprovider tests -q
node --check static/weave-v2.js
```

## Scope

The live web proof is deterministic and credential-free. It creates temporary Git worktrees only; it does not start a Vibe session or modify a user repository. Live Vibe execution remains opt-in through the project-local hooks.

## License

MIT
