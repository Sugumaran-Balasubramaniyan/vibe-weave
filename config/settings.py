"""Configuration settings for GlassBox Sentinel."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import yaml

load_dotenv()

# Load entropy defaults from YAML
CONFIG_DIR = Path(__file__).parent
with open(CONFIG_DIR / "entropy.defaults.yaml", "r") as f:
    entropy_defaults = yaml.safe_load(f)


class Settings:
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # Mistral API
    mistral_api_key: Optional[str] = os.getenv("MISTRAL_API_KEY")
    mistral_base_url: str = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
    mistral_compressor_model: str = os.getenv("MISTRAL_COMPRESSOR_MODEL", "mistral-small-latest")
    mistral_observer_model: str = os.getenv("MISTRAL_OBSERVER_MODEL", "ministral-8b-latest")

    # Demo mode - never call live API
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

    # Authenticates project-local Mistral Vibe hook adapters. Keep this
    # per-install secret outside version control.
    vibe_hook_token: Optional[str] = os.getenv("GLASSBOX_VIBE_TOKEN") or os.getenv("GLASSBOX_VIBE_HOOK_TOKEN")

    # Entropy configuration
    window_w: int = entropy_defaults.get("window_w", 5)
    consecutive_error_n: int = entropy_defaults.get("consecutive_error_n", 3)
    no_progress_p: int = entropy_defaults.get("no_progress_p", 4)
    max_steps: int = entropy_defaults.get("max_steps", 20)
    threshold: float = entropy_defaults.get("threshold", 0.65)
    weights: dict = entropy_defaults.get("weights", {})
    step_delay_ms_min: int = entropy_defaults.get("step_delay_ms_min", 400)
    step_delay_ms_max: int = entropy_defaults.get("step_delay_ms_max", 800)


settings = Settings()
