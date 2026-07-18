"""Entropy computation and brake logic for GlassBox Sentinel."""

from typing import List, Optional
from dataclasses import dataclass, field
import re
from collections import Counter

from app.models import AgentStep, AgentStepStatus, EntropyBreakdown


@dataclass
class EntropyConfig:
    window_w: int = 5
    consecutive_error_n: int = 3
    no_progress_p: int = 4
    max_steps: int = 20
    threshold: float = 0.65
    weights: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.weights:
            self.weights = {
                'repeat_error_density': 0.40,
                'action_loop_density': 0.25,
                'no_progress': 0.25,
                'step_budget_pressure': 0.10,
            }


def _normalize_signature(sig: Optional[str]) -> str:
    """Normalize error signature for comparison."""
    if not sig:
        return ""
    # Strip timestamps, PIDs, absolute paths, hex IDs
    sig = re.sub(r'\[\d{4}-\d{2}-\d{2}', '', sig)
    sig = re.sub(r'pid=\d+', '', sig)
    sig = re.sub(r'/[a-f0-9]{8,}/', '/.../', sig)
    return sig.strip()


def compute_entropy(steps: List[AgentStep], config: EntropyConfig) -> EntropyBreakdown:
    """Compute entropy score from list of steps."""
    if not steps:
        return EntropyBreakdown(
            score=0.0,
            threshold=config.threshold,
            components={},
            reasons=[],
            braking=False
        )

    W = config.window_w
    P = config.no_progress_p
    window = steps[-W:] if len(steps) >= W else steps

    # 1. repeat_error_density
    # Count occurrences of error signatures in window
    sig_counts = Counter(
        _normalize_signature(s.error_signature) 
        for s in window 
        if s.error_signature
    )
    max_sig_count = max(sig_counts.values()) if sig_counts else 0
    repeat_error_density = min(1.0, max_sig_count / W) if W > 0 else 0.0

    # 2. action_loop_density
    action_pairs = [(s.action, s.input_summary) for s in window]
    pair_counts = Counter(action_pairs)
    max_pair_count = max(pair_counts.values()) if pair_counts else 0
    action_loop_density = min(1.0, max_pair_count / W) if W > 0 else 0.0

    # 3. no_progress
    # Check if any ok step with files_touched change in last P steps
    last_p = steps[-P:] if len(steps) >= P else steps
    has_progress = any(
        s.status == AgentStepStatus.ok and s.files_touched
        for s in last_p
    )
    has_partial = any(
        s.status in [AgentStepStatus.noop, AgentStepStatus.thinking]
        for s in last_p
    )
    no_progress = 0.0
    if not has_progress:
        no_progress = 1.0 if not has_partial else 0.5

    # 4. step_budget_pressure
    step_index = len(steps) - 1
    step_budget_pressure = min(1.0, step_index / config.max_steps)

    # Compute score
    score = (
        config.weights.get('repeat_error_density', 0.40) * repeat_error_density +
        config.weights.get('action_loop_density', 0.25) * action_loop_density +
        config.weights.get('no_progress', 0.25) * no_progress +
        config.weights.get('step_budget_pressure', 0.10) * step_budget_pressure
    )
    score = max(0.0, min(1.0, score))  # clamp01

    # Check consecutive identical error signatures
    consecutive_count = 0
    max_consecutive = 0
    last_sig = None
    for s in reversed(steps):
        sig = _normalize_signature(s.error_signature)
        if sig and sig == last_sig:
            consecutive_count += 1
        else:
            consecutive_count = 1 if sig else 0
            last_sig = sig
        max_consecutive = max(max_consecutive, consecutive_count)

    # Determine braking
    braking = score >= config.threshold or max_consecutive >= config.consecutive_error_n

    # Generate reasons
    reasons = []
    if max_consecutive >= config.consecutive_error_n:
        reasons.append(f"Same error_signature repeated {max_consecutive} times consecutive")
    if repeat_error_density >= 1.0:
        reasons.append(f"Same error_signature repeated {max_sig_count} times")
    if no_progress >= 1.0:
        reasons.append(f"No successful file progress in last {P} steps")
    if score >= config.threshold:
        reasons.append(f"Entropy score {score:.2f} >= threshold {config.threshold}")

    # Store consecutive count in components for reference
    components = {
        'repeat_error_density': round(repeat_error_density, 4),
        'action_loop_density': round(action_loop_density, 4),
        'no_progress': round(no_progress, 4),
        'step_budget_pressure': round(step_budget_pressure, 4),
    }

    return EntropyBreakdown(
        score=round(score, 4),
        threshold=config.threshold,
        components=components,
        reasons=reasons,
        braking=braking
    )


def should_brake(entropy: EntropyBreakdown, consecutive_error_count: int,
                 config: EntropyConfig) -> bool:
    """Determine if brake should be applied."""
    return entropy.braking or consecutive_error_count >= config.consecutive_error_n
