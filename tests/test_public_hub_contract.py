"""Contract coverage for the public Vibe Weave site."""

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app.main import app


HUB_TABS = ("overview", "proof", "architecture", "vibe", "demo")


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        element = {key: value or "" for key, value in attrs}
        element["_tag"] = tag
        self.elements.append(element)


@pytest.fixture
def client():
    return TestClient(app)


def test_root_serves_complete_accessible_vibe_weave_hub(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Vibe Weave" in response.text
    assert "GlassBox Sentinel" not in response.text
    parser = ElementCollector()
    parser.feed(response.text)
    tabs = [item for item in parser.elements if item.get("role") == "tab"]
    panels = [item for item in parser.elements if item.get("role") == "tabpanel"]
    assert len(tabs) == len(HUB_TABS) == len(panels)
    for name in HUB_TABS:
        assert any(item.get("id") == f"tab-{name}" and item.get("aria-controls") == f"panel-{name}" for item in tabs)
        assert any(item.get("id") == f"panel-{name}" and item.get("aria-labelledby") == f"tab-{name}" for item in panels)


def test_hub_exposes_live_proof_architecture_and_demo_script(client):
    page = client.get("/").text
    for element_id in ("run-weave-proof", "weave-question", "decision-contract", "verification-result", "play-walkthrough"):
        assert f'id="{element_id}"' in page
    assert "never starts a Vibe session" in page
    assert "real disposable Git worktrees" in page


def test_public_proof_endpoint_returns_deterministic_report(client):
    response = client.post("/api/v1/weave/drill?decision=admin_only")
    assert response.status_code == 200
    report = response.json()
    assert report["product"] == "Vibe Weave"
    assert report["verification"]["passed"] is True
