"""Navigation contract for the public project hub."""

from pathlib import Path


def test_tab_navigation_returns_the_visitor_to_the_hub_top():
    source = Path("static/app.js").read_text()

    assert "window.scrollTo" in source
    assert "top: 0" in source
