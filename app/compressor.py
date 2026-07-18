"""Compression service for GlassBox Sentinel - LLM and fallback."""

import json
import logging
from typing import Tuple

from app.models import AgentStep, AgentStepStatus, SaveState, DecisionTree, DecisionTreeNode, DecisionTreeNodeKind
from config.settings import Settings

logger = logging.getLogger(__name__)


class Compressor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load compressor system prompt from file."""
        try:
            with open('app/prompts/compress_system.prompt.txt', 'r') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback system prompt
            return (
                "You are the GlassBox Sentinel compressor for a coding-agent control plane.\n"
                "Given a goal and a list of agent steps, produce a single JSON object only.\n"
                "Produce save_state and decision_tree."
            )

    def _fallback_compress(self, run_id: str, steps: list[AgentStep],
                          goal: str) -> Tuple[SaveState, DecisionTree]:
        """Build fallback save_state and decision_tree from steps."""
        worked = []
        failed = []
        last_good = None

        for step in steps:
            if step.status == AgentStepStatus.ok:
                if step.files_touched:
                    worked.append(f"{step.title}")
                last_good = step.id
            elif step.status == AgentStepStatus.error:
                failed.append(f"{step.title} - {step.error_signature or 'unknown error'}")

        # Find unique error signatures
        error_sigs = set(s.error_signature for s in steps if s.error_signature)
        blocked_on = "; ".join(error_sigs) if error_sigs else "Unknown error"

        save_state = SaveState(
            run_id=run_id,
            status="braked",
            goal=goal,
            worked=worked if worked else ["Initial scaffolding completed"],
            failed=failed if failed else ["Database migration failed"],
            last_good_checkpoint=last_good,
            blocked_on=f"Stuck on: {blocked_on}",
            recommended_next_actions=[
                f"Try a different approach for {next(iter(error_sigs), 'the failing step')}"
            ],
            context_summary=f"Completed {len(worked)} steps successfully. "
                           f"Encountered {len(failed)} errors. "
                           f"Last good checkpoint: {last_good}",
            compress_source="fallback"
        )

        # Build decision tree
        root = DecisionTreeNode(
            id="n0",
            label=f"Goal: {goal}",
            kind=DecisionTreeNodeKind.goal,
            children=[]
        )

        # Add success branch
        if worked:
            success_node = DecisionTreeNode(
                id="n1",
                label="Completed steps",
                kind=DecisionTreeNodeKind.success,
                children=[]
            )
            root.children.append(success_node)

        # Add failure branch with loop and brake
        if failed:
            failure_node = DecisionTreeNode(
                id="n2",
                label="Failed steps",
                kind=DecisionTreeNodeKind.failure,
                children=[]
            )

            loop_node = DecisionTreeNode(
                id="n3",
                label=f"Loop detected ({len(failed)} errors)",
                kind=DecisionTreeNodeKind.loop,
                children=[]
            )
            failure_node.children.append(loop_node)

            brake_node = DecisionTreeNode(
                id="n4",
                label="Human override required",
                kind=DecisionTreeNodeKind.brake,
                children=[]
            )
            failure_node.children.append(brake_node)

            root.children.append(failure_node)

        decision_tree = DecisionTree(
            root=root,
            highlight_path=["n0", "n2", "n3", "n4"] if failed else ["n0", "n1"]
        )

        return save_state, decision_tree

    async def compress(self, run_id: str, steps: list[AgentStep],
                       goal: str) -> Tuple[SaveState, DecisionTree]:
        """Compress steps into save_state and decision_tree.
        
        Uses LLM if API key available and not in demo mode,
        otherwise falls back to template-based compression.
        """
        if self.settings.demo_mode or not self.settings.mistral_api_key:
            logger.info("Using fallback compressor (demo mode or no API key)")
            return self._fallback_compress(run_id, steps, goal)

        # Build prompt for LLM
        prompt = self._build_prompt(run_id, steps, goal)

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.settings.mistral_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.mistral_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.mistral_compressor_model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.0,
                        "max_tokens": 2000,
                    },
                )
                response.raise_for_status()
                text = response.json()["choices"][0]["message"]["content"]
                return self._parse_response(text)
        except Exception as e:
            logger.warning(f"Compression failed: {e}, falling back to template")
            return self._fallback_compress(run_id, steps, goal)

    def _build_prompt(self, run_id: str, steps: list[AgentStep], goal: str) -> str:
        """Build the prompt for the LLM."""
        steps_json = json.dumps([s.model_dump() for s in steps], indent=2)
        return f"""{self.system_prompt}

Goal: {goal}
Run ID: {run_id}
Steps:
{steps_json}

Produce JSON only:
"""

    def _parse_response(self, text: str) -> Tuple[SaveState, DecisionTree]:
        """Parse LLM response into SaveState and DecisionTree."""
        import re
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            save_state = SaveState(**data['save_state'])
            decision_tree = DecisionTree(**data['decision_tree'])
            return save_state, decision_tree
        raise ValueError("No valid JSON found in response")
