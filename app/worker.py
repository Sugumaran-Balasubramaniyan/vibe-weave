"""Worker for executing scenario steps in GlassBox Sentinel."""

import asyncio
import logging
import random
from datetime import datetime, timezone

from app.models import AgentStep, AgentStepStatus, AgentStepType, RunStatus
from app.entropy import compute_entropy, should_brake, EntropyConfig
from app.compressor import Compressor
from app.run_manager import RunManager
from app.scenarios import load_scenario

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, run_id: str, scenario_id: str, run_manager: RunManager,
                 entropy_config: EntropyConfig, compressor: Compressor,
                 step_delay_ms: tuple = (400, 800)):
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.run_manager = run_manager
        self.entropy_config = entropy_config
        self.compressor = compressor
        self.step_delay_ms = step_delay_ms
        self._resume_event = asyncio.Event()
        self._stop_event = asyncio.Event()

    async def _create_step(self, index: int, step_data: dict) -> AgentStep:
        """Create an AgentStep from scenario step data."""
        return AgentStep(
            id=f"step-{index:03d}",
            index=index,
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=AgentStepType(step_data.get('type', 'system')),
            title=step_data.get('title', f'Step {index}'),
            action=step_data.get('action', 'unknown'),
            input_summary=step_data.get('input_summary', ''),
            output_summary=step_data.get('output_summary', ''),
            status=AgentStepStatus(step_data.get('status', 'ok')),
            error_signature=step_data.get('error_signature'),
            files_touched=step_data.get('files_touched', []),
            raw=step_data.get('raw'),
        )

    async def run(self):
        """Execute the scenario worker loop."""
        logger.info(f"Worker starting for run {self.run_id}, scenario {self.scenario_id}")

        scenario = load_scenario(self.scenario_id)
        if not scenario:
            logger.error(f"Scenario {self.scenario_id} not found")
            await self.run_manager.set_status(self.run_id, RunStatus.failed,
                                               error="Scenario not found")
            return

        # Update run state with scenario details
        await self.run_manager.update_run(self.run_id, {
            'goal': scenario.get('goal', ''),
            'scenario_id': self.scenario_id,
        })
        await self.run_manager.set_status(self.run_id, RunStatus.running)

        steps = []
        consecutive_error_count = 0
        last_error_sig = None

        scenario_steps = scenario.get('steps', [])

        for i, step_data in enumerate(scenario_steps):
            if self._stop_event.is_set():
                await self.run_manager.set_status(
                    self.run_id, RunStatus.failed, error="Worker stopped"
                )
                return

            # Create and append step
            step = await self._create_step(i, step_data)
            steps.append(step)

            # Update consecutive error count
            if step.status == AgentStepStatus.error and step.error_signature:
                if step.error_signature == last_error_sig:
                    consecutive_error_count += 1
                else:
                    consecutive_error_count = 1
                    last_error_sig = step.error_signature
            else:
                consecutive_error_count = 0
                last_error_sig = None

            # Emit step event
            await self.run_manager.emit_event(self.run_id, 'step', step.model_dump())

            # Compute entropy
            entropy = compute_entropy(steps, self.entropy_config)
            await self.run_manager.update_run(self.run_id, {
                'steps': steps,
                'entropy': entropy,
            })
            await self.run_manager.emit_event(self.run_id, 'entropy', entropy.model_dump())

            # Check brake condition
            if should_brake(entropy, consecutive_error_count, self.entropy_config):
                logger.info(f"Brake triggered for run {self.run_id}: "
                           f"score={entropy.score}, consecutive={consecutive_error_count}")

                # Set braked status
                await self.run_manager.set_status(self.run_id, RunStatus.braked)

                # Compress
                try:
                    save_state, decision_tree = await self.compressor.compress(
                        self.run_id, steps, scenario.get('goal', '')
                    )
                    compress_source = "live"
                except Exception as e:
                    logger.warning(f"Compression failed, using fallback: {e}")
                    save_state, decision_tree = self.compressor._fallback_compress(
                        self.run_id, steps, scenario.get('goal', '')
                    )
                    compress_source = "fallback"

                # Update meta
                run = await self.run_manager.get_run(self.run_id)
                if run:
                    run.meta['compress_source'] = compress_source

                # Update run with save_state and tree
                await self.run_manager.update_run(self.run_id, {
                    'save_state': save_state,
                    'decision_tree': decision_tree,
                })

                # Emit events
                await self.run_manager.emit_event(self.run_id, 'braked', {
                    'run_id': self.run_id,
                    'reason': 'consecutive_error_signature' if consecutive_error_count >= self.entropy_config.consecutive_error_n else 'score_threshold',
                    'entropy': entropy.model_dump(),
                })
                voice_alert_text = "Agent is stuck in a loop. Human override required."
                await self.run_manager.update_run(self.run_id, {
                    'voice_alert_text': voice_alert_text,
                })
                await self.run_manager.emit_event(self.run_id, 'voice', {
                    'run_id': self.run_id,
                    'text': voice_alert_text,
                })
                await self.run_manager.emit_event(self.run_id, 'save_state',
                                                  save_state.model_dump())
                await self.run_manager.emit_event(self.run_id, 'tree',
                                                  decision_tree.model_dump())

                # Wait for override
                logger.info(f"Run {self.run_id} braked, waiting for override...")
                await self._resume_event.wait()

                if self._stop_event.is_set():
                    await self.run_manager.set_status(
                        self.run_id, RunStatus.failed, error="Worker stopped"
                    )
                    return

                # Override received - continue with recovery
                logger.info(f"Run {self.run_id} override received, resuming...")
                await self.run_manager.set_status(self.run_id, RunStatus.running_resume)
                await self.run_manager.emit_event(self.run_id, 'resumed',
                                                  {'run_id': self.run_id})

                # Recovery is bound to the authorized scenario option, never arbitrary text.
                run_state = await self.run_manager.get_run(self.run_id)
                choice_id = run_state.meta.get("recovery_authorized_choice_id") if run_state else None
                recovery_steps = scenario.get("recovery_steps_by_choice", {}).get(choice_id, [])
                if not choice_id or not recovery_steps:
                    await self.run_manager.set_status(
                        self.run_id, RunStatus.failed, error="No authorized recovery path"
                    )
                    return
                selection = run_state.meta.get("recovery_selection", {})
                option = next(
                    (item for item in run_state.meta.get("recovery_options", [])
                     if item.get("id") == choice_id),
                    {},
                )
                for j, recovery_step_data in enumerate(recovery_steps):
                    if self._stop_event.is_set():
                        await self.run_manager.set_status(
                            self.run_id, RunStatus.failed, error="Worker stopped"
                        )
                        return

                    recovery_step_data = recovery_step_data.copy()
                    recovery_step_data["input_summary"] = recovery_step_data.get("input_summary", "").replace(
                        "{{recovery_option_label}}", option.get("label", choice_id)
                    ).replace(
                        "{{operator_rationale}}", selection.get("rationale", "No operator rationale provided.")
                    )

                    recovery_step = await self._create_step(
                        len(steps) + j, recovery_step_data
                    )
                    steps.append(recovery_step)

                    await self.run_manager.emit_event(self.run_id, 'step',
                                                      recovery_step.model_dump())

                    # Small delay
                    await asyncio.sleep(0.1)

                # Update run state
                await self.run_manager.update_run(self.run_id, {
                    'steps': steps,
                })

                await self.run_manager.set_status(self.run_id, RunStatus.completed)
                await self.run_manager.emit_event(self.run_id, 'completed', {
                    'run_id': self.run_id,
                    'status': 'completed',
                })
                break

            # Delay between steps
            delay = random.uniform(self.step_delay_ms[0], self.step_delay_ms[1]) / 1000.0
            await asyncio.sleep(delay)
        else:
            # No brake, completed normally
            await self.run_manager.set_status(self.run_id, RunStatus.completed)
            await self.run_manager.emit_event(self.run_id, 'completed', {
                'run_id': self.run_id,
                'status': 'completed',
            })

    def resume(self):
        """Signal a braked worker to run its recovery steps."""
        self._resume_event.set()

    def stop(self):
        """Stop the worker and release it if it is waiting for an override."""
        self._stop_event.set()
        self._resume_event.set()
