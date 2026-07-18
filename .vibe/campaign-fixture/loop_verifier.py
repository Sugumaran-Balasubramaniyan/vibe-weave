"""Harmless deterministic failure used by the Vibe hook campaign."""

import sys


print("GLASSBOX_CAMPAIGN_REPEAT: expected harmless verifier failure")
raise SystemExit(1)
