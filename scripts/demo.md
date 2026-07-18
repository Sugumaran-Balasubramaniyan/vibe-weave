# Deterministic Demo and Video Runbook

## Before recording

1. Use a clean browser tab and start the app with `make run`.
2. Open `http://localhost:8000/` and select **Live Demo**.
3. Confirm the **Vibe connection** panel says `Fixture scenario — no Vibe hook attached`. This is expected: the recording uses a deterministic fixture, not a local Vibe session.
4. Keep `DEMO_MODE=true` or leave `MISTRAL_API_KEY` unset for a fully offline-safe presentation.

## Live sequence

1. Start the demo and state the goal: add a users migration and `GET /users`.
2. Point to the successful scaffold steps, then the three matching `db.migration.relation_exists` failures.
3. Explain that Glass Box brakes on either the explainable Loop Risk threshold or three consecutive matching errors.
4. At the brake, show the save state and decision tree. Say that this is the handoff an operator uses; it is not an autonomous recovery decision.
5. Call out the Vibe panel: it is an optional, privacy-bounded adapter surface. Live runs use redacted, bounded action/result summaries rather than full transcripts; workspace paths and credentials never reach Glass Box.
6. Submit the displayed additive-migration override: `Don't recreate users; use alter table add column email only.`
7. Show the override acknowledgement, resumed status, recovery steps, and completed state.

## Video-safe narration

> “Glass Box sees repeated failure, stops the loop with a transparent rule, preserves the useful state, and waits for a human to authorize the next action. The demo is deterministic. The checked-in Vibe hook can contribute a minimal, sanitized event envelope when configured, without exposing the Vibe workspace or session contents.”

## If the demo is interrupted

1. Refresh the page and select **Live Demo** again.
2. Start a new fixture run; do not reuse an old run ID.
3. If the browser loses the event stream, refresh once before recording. The dashboard also polls the run state as a fallback.

## Do not claim

- that the fixture demo is executing a live Vibe session;
- that Glass Box reads a Vibe workspace or local session files;
- that the detector chooses recovery by itself;
- that API keys, workspace paths, prompts, source code, or full raw tool transcripts are sent to the dashboard.

For the payload and privacy contract, see `docs/VIBE-INTEGRATION.md`.
