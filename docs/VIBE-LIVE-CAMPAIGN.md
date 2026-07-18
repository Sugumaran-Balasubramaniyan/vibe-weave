# Live Vibe Campaign: Baseline vs. Guarded Loop

## Purpose

This opt-in campaign runs the same harmless, deterministic verifier through two real Vibe programmatic sessions. It demonstrates the difference between an unhooked baseline and a defended worktree that loads GlassBox Sentinel's checked-in `pre_tool` and `post_tool` hooks.

The verifier only prints a fixed marker and exits `1`; it does not edit files, contact services, or access project data.

## Preconditions

- Mistral Vibe 2.21+ is installed and already authenticated for programmatic `--prompt` use.
- GlassBox Sentinel is running with its Vibe hook token configured.
- Export the same token locally, along with the endpoint:

```bash
export GLASSBOX_VIBE_TOKEN='your-untracked-hook-token'
export GLASSBOX_VIBE_EVENTS_URL='https://www.glassbox.sugumaran-balasubramaniyan.com/api/v1/vibe/events'
```

Never commit this token, a populated `.env`, campaign output, or a hook configuration that includes a token.

## Quick start

1. Validate only the local CLI, Git, and harmless fixture. This does not call Vibe or the GlassBox Sentinel service.

   ```bash
   scripts/run_vibe_campaign.sh --check
   ```

2. Start the two live sessions after preflight succeeds:

   ```bash
   scripts/run_vibe_campaign.sh --live
   ```

The runner verifies the authenticated GlassBox Sentinel control endpoint before any Vibe session begins. It cannot safely preflight a Vibe API credential; if Vibe rejects authentication or reaches a campaign limit, the runner exits non-zero and leaves an exact JSON log path.

## What the runner isolates

For each variant it creates a new temporary Git repository, commits only the harmless verifier, and invokes Vibe with both `--prompt` and `--worktree`.

- **Baseline** has no project `.vibe/hooks.toml`, so the verifier's requested repeated failures are observed only by Vibe.
- **Defended** copies the project's hook configuration and links only the project-local `scripts/glassbox_vibe_hook.py` adapter. Its `post_tool` observations reach GlassBox Sentinel; after the repeated error threshold, the next `pre_tool` call is denied by the hook.

The prompt instructs Vibe to run `python3 loop_verifier.py` four times. The fourth request is intentional: the third failed post-tool event creates the brake, and the following pre-tool boundary is where Vibe can enforce the denial.

## Expected evidence

| Variant | Expected result |
| --- | --- |
| Baseline | Four harmless verifier attempts, subject only to Vibe's normal agent behavior and limits. |
| Defended | Repeated failures are ingested, GlassBox Sentinel brakes, and a subsequent tool request is denied until an operator supplies the live override. |

The runner writes `baseline.json`, `defended.json`, and `campaign-report.txt` to a new `/tmp/glassbox-vibe-campaign.*` directory by default. Use `--output DIR` or `GLASSBOX_CAMPAIGN_OUTPUT_DIR` to choose a different artifact directory. Review artifacts before sharing them.

## Worktree and hook details

Vibe 2.21 discovers trusted project hooks at `<project>/.vibe/hooks.toml`; `pre_tool` runs before a tool and can deny it, while `post_tool` runs only after the tool body executes. The runner uses independent temporary Git roots so the baseline does not inherit the defended project's hook file. It intentionally preserves Vibe's programmatic worktrees for inspection.

If `~/.vibe/hooks.toml` exists, disable or account for it before comparing results: global hooks would contaminate the baseline.

## Failure and fallback

- A missing `GLASSBOX_VIBE_TOKEN` stops `--live` before Vibe is invoked.
- A failed authenticated control check stops `--live` before Vibe is invoked.
- A Vibe authentication, budget, or model failure is recorded in that variant's JSON log; fix credentials or limits and rerun with a fresh output directory.

When live credentials are unavailable, `--check` remains an executable no-network validation of the fixture and runner syntax. It is the supported fallback, not a simulated campaign result.

## Security boundary

The campaign inherits the adapter's bounded redaction policy. Do not put secrets in the prompt, verifier command, output directory name, or any Vibe hook configuration. The fixture contains no credentials and makes no network calls.
