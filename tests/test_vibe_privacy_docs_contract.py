"""Regression checks for the public Vibe privacy wording."""

from pathlib import Path


def test_vibe_docs_describe_bounded_summaries_and_path_boundary():
    docs = Path("docs/VIBE-INTEGRATION.md").read_text()
    hub = Path("static/hub.html").read_text()
    readme = Path("README.md").read_text()

    assert "bounded, redacted action and result summaries" in docs
    assert "never sends `cwd`, raw path fields" in docs
    assert "`input_summary`, `output_summary`" in docs
    assert "tool input/output, shell commands, or workspace paths" not in docs
    assert "redacted, bounded action/result summaries" in hub
    assert "redacted, bounded action/result summaries" in readme
