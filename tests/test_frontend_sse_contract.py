"""Contract checks between the named SSE stream and browser client."""

from pathlib import Path


def test_browser_registers_listeners_for_all_named_run_events():
    source = Path("static/app.js").read_text()

    for event_name in (
        "snapshot",
        "step",
        "entropy",
        "braked",
        "save_state",
        "tree",
        "status",
        "override_accepted",
        "resumed",
        "completed",
        "voice",
    ):
        assert event_name in source

    assert "addEventListener(eventType" in source



def test_browser_registers_guarded_recovery_events_and_authorization_flow():
    source = Path("static/app.js").read_text()
    hub = Path("static/hub.html").read_text()

    for event_name in ("recovery_selected", "recovery_rejected", "recovery_authorized"):
        assert f"\x27{event_name}\x27" in source or f"\x22{event_name}\x22" in source

    assert "choice_id: choiceId" in source
    assert "/override/authorize" in source
    assert "option?.authorizing" in source
    assert "Sentinel can autonomously contain" in hub


def test_browser_renders_state_derived_live_explainer():
    source = Path("static/app.js").read_text()
    hub = Path("static/hub.html").read_text()

    for stage in ("observe", "contain", "compile", "verify", "continue"):
        assert f'data-sentinel-stage="{stage}"' in hub
        assert f'sentinel-{stage}-detail' in hub

    assert "updateSentinelProofFlow" in source
    assert "updateBrakeExplanation" in source



def test_browser_handles_mutation_envelopes_backend_recovery_metadata_and_reset():
    source = Path("static/app.js").read_text()

    assert "payload.run && typeof payload.run === \"object\" ? payload.run : payload" in source
    assert "meta.recovery_selection" in source
    assert "selection.choice_id" in source
    assert "meta.recovery_authorized_choice_id" in source
    assert "this.runId = null" in source
    assert "this.currentRun = null" in source
    assert "this.elements.startButton.disabled = false" in source



def test_browser_registers_immunity_compiler_campaign_contract():
    source = Path("static/app.js").read_text()
    hub = Path("static/hub.html").read_text()

    assert "immunity_compiler_campaign" in source
    for event_name in ("campaign_preparing", "campaign_detected", "campaign_repaired", "campaign_verified"):
        assert event_name in source
    for field_name in ("attack_path", "minimal_reproducer", "verified_policy_repair"):
        assert field_name in source
    for element_id in ("start-campaign", "attack-path", "minimal-reproducer", "verified-policy-repair"):
        assert element_id in hub
    assert "updateCampaignPanels" in source
