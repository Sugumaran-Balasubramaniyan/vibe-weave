# Future integration plan: Mistral Vibe × Vibe Weave

This is a proposed integration plan, not a claim that these features already exist upstream.

## Goal

Let a Mistral Vibe project opt into a lightweight coordination checkpoint when it delegates work to multiple agents.

```text
Vibe delegates roles
        ↓
roles propose Change Contracts
        ↓
Weave finds a conflict, if any
        ↓
Vibe asks one focused question
        ↓
Decision Contract unlocks scoped implementation
```

## Design principles

1. **Opt in, never surprise.** A normal Vibe task keeps its existing behavior.
2. **Ask fewer questions.** Only surface the highest-impact unresolved decision.
3. **Keep contracts small.** Store decisions, file scope, public interfaces, and proofs—not full prompts or transcripts.
4. **Fail visibly.** A conflict should explain what disagreed and what decision would unblock it.
5. **Use Vibe primitives.** Build on project-local agents, skills, hooks, and worktrees rather than replacing orchestration.

## Phased implementation

### Phase 0 — Companion package (current repository)

- `python -m vibe_weave drill` demonstrates the model without credentials.
- `.vibe/skills/vibe-weave/SKILL.md` teaches agents to propose contracts.
- `.vibe/hooks.toml` blocks managed writes while stored state has an unresolved conflict.

**Exit criterion:** a developer can understand the behavior from one terminal command and one JSON report.

### Phase 1 — First-class contract command

Propose a Vibe command shape such as:

```bash
vibe weave propose --role backend --contract .vibe/weave/backend.json
vibe weave check
```

Expected output:

```text
Conflict: invoice_export.authorization
  frontend: authenticated_user
  backend:  admin_only

Question: Who may export invoices?
```

**Exit criterion:** no custom Python is needed to inspect contracts and conflicts.

### Phase 2 — Delegation handshake

When Vibe launches a multi-role task:

1. Ask every role for a structured Change Contract before write tools.
2. Merge and rank conflicts.
3. Use Vibe’s question surface for the single highest-impact question.
4. Write `.vibe/weave/decision.json` after the answer.

**Exit criterion:** parallel roles begin implementation with one shared decision record.

### Phase 3 — Scoped worktree execution

Use Vibe worktrees to separate implementation roles. Each role receives:

- its resolved contract;
- its permitted file scope;
- its required proofs; and
- the shared Decision Contract.

At integration time, Vibe shows a concise report:

```text
Decision: admin_only
Roles aligned: 3/3
Proofs passed: 3/3
Files outside declared scope: 0
```

**Exit criterion:** a reviewer can understand both the code and the decision that shaped it.

### Phase 4 — Guard and review UX

Refine the existing pre-tool guard so it can explain:

- why a write is held;
- which decision remains open;
- what answer options exist; and
- how to resume safely.

Add a Markdown summary to the Vibe session output and optionally attach it to a pull request.

**Exit criterion:** blocking behavior feels like useful guidance, not a mysterious failure.

## Suggested upstream contribution slices

Keep each contribution reviewable and independently useful:

1. Contract schema and validation.
2. Conflict detector plus terminal formatter.
3. Project-local skill and agent template.
4. Hook adapter with transparent default behavior.
5. Worktree integration and final report.

## Security and privacy

- Do not place raw prompts, tool input, credentials, or workspace paths in contracts.
- Keep decision records project-local unless a developer explicitly exports them.
- Treat shell commands as managed writes only when enforcement is enabled.
- Preserve a manual bypass for emergency debugging, but make the bypass auditable.

## What success looks like

A junior engineer should be able to say: “Before agents work in parallel, Weave makes them write down what they mean. If they disagree, it asks one question. Once they agree, Vibe builds and proves the result.”
