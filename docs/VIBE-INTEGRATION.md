# Vibe Integration Contract

## Scope

GlassBox Sentinel is a control plane, not a Vibe session reader. The bundled demo is deterministic and fixture-driven; it does not launch Mistral Vibe, inspect a workspace, or load a local session transcript.

The checked-in server-side Vibe hook normalizes authenticated Vibe events into the existing run lifecycle when its hook token is configured.

- The adapter owns Vibe access and policy enforcement.
- The control plane owns loop-risk scoring, braking, and override acceptance.
- The browser receives only an allow-listed display envelope.

It is safe to run the public fixture demo with no Vibe installation or Vibe credentials.

## Allow-listed metadata

The dashboard progressively recognizes the following optional values on a run payload:

```json
{
  "meta": {
    "vibe": {
      "source": "mistral-vibe-hook",
      "session_label": "checkout-api-demo",
      "hook_status": "connected"
    }
  }
}
```

`meta.vibe_source`, `meta.vibe_session_label`, `meta.vibe_session_id`, and `meta.vibe_hook_status` are also accepted for a transitional flat payload. Values must be short strings or numbers. The browser rejects values longer than 120 characters and values that look like credentials.

## Privacy boundary

GlassBox Sentinel stores bounded, redacted action and result summaries for a live Vibe run. These are observability summaries, not complete command or result transcripts.

The hook must remove workspace paths and credentials before it sends an event. It never sends `cwd`, raw path fields, API keys, tokens, passwords, authorization headers, cookies, or secrets.

## Event envelope

The hook sends only the fields needed to correlate and score a tool event:

| Field | Contract |
| --- | --- |
| `source`, `event_id`, `session_id`, `tool_call_id` | Run and event identity. A session identifier is display metadata, not an authorization credential. |
| `phase`, `event_type`, `tool_name`, `status`, `duration_ms` | Normalized tool lifecycle information. |
| `input_summary`, `output_summary` | Redacted, bounded summaries; never full transcripts. |
| `error_signature` | Redacted, normalized failure signal for loop detection. |

The adapter must never publish raw prompts, conversation history, source code, file contents, workspace paths, or unredacted error payloads. Normalize those events before they enter the control plane; publish only this envelope and the metadata allow list above.

## Live Vibe setup

Configure the server and the Vibe client with the same token. Do this only in untracked local configuration.

1. On the GlassBox Sentinel server, add a strong value to the untracked service `.env` file:

   ```bash
   GLASSBOX_VIBE_TOKEN=replace-with-a-strong-local-secret
   ```

2. Restart the GlassBox Sentinel service so it loads the new environment variable.

3. In the shell that will launch Vibe, export that exact same token and the public hook endpoint **before** running `vibe --trust`:

   ```bash
   export GLASSBOX_VIBE_TOKEN='replace-with-the-same-local-secret'
   export GLASSBOX_VIBE_EVENTS_URL='https://www.glassbox.sugumaran-balasubramaniyan.com/api/v1/vibe/events'
   vibe --trust
   ```

Never commit the token, a populated `.env`, or hook configuration containing it. Keep any Vibe hook configuration local and untracked.

## UI behavior

