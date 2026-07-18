---
name: vibe-weave
description: Coordinate delegated implementation work with Change Contracts before code edits.
---

# Vibe Weave

Before delegating multi-agent implementation work, ask each participating role to return one JSON Change Contract with: `id`, `role`, `goal`, `files`, `decisions`, `public_contracts`, and `proofs`.

Run `python3 -m vibe_weave drill` for the credential-free authorization-scope proof. When contracts disagree on a decision, ask the user only the highest-impact unresolved question. Do not begin managed edits until a Decision Contract is written under `.vibe/weave/`.

Use separate worktrees for implementation roles. Each role may edit only files listed in its resolved Change Contract and must run its listed proofs before integration.
