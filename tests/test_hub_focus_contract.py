"""Accessibility contract for programmatic hub navigation."""

from pathlib import Path


def test_overview_demo_cta_moves_focus_to_the_demo_tab():
    source = Path("static/app.js").read_text()

    assert 'document.getElementById(`tab-${target}`).focus()' in source
