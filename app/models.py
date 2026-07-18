"""Pydantic models for GlassBox Sentinel."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field



class AgentStepStatus(str, Enum):
    ok = "ok"
    error = "error"
    noop = "noop"
    thinking = "thinking"
    override = "override"


class AgentStepType(str, Enum):
    thinking = "thinking"
    tool_call = "tool_call"
    write_file = "write_file"
    override = "override"
    system = "system"


class DecisionTreeNodeKind(str, Enum):
    goal = "goal"
    success = "success"
    failure = "failure"
    loop = "loop"
    brake = "brake"
    override = "override"
    recovered = "recovered"


class RunStatus(str, Enum):
    idle = "idle"
    running = "running"
    braked = "braked"
    running_resume = "running_resume"
    completed = "completed"
    failed = "failed"


class AgentStep(BaseModel):
    id: str
    index: int
    timestamp: str  # ISO format
    type: AgentStepType
    title: str
    action: str
    input_summary: str
    output_summary: str
    status: AgentStepStatus
    error_signature: Optional[str] = None
    files_touched: List[str] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None


class EntropyBreakdown(BaseModel):
    score: float
    threshold: float
    components: Dict[str, float]
    reasons: List[str]
    braking: bool


class DecisionTreeNode(BaseModel):
    id: str
    label: str
    kind: DecisionTreeNodeKind
    children: List["DecisionTreeNode"] = Field(default_factory=list)


class DecisionTree(BaseModel):
    root: DecisionTreeNode
    highlight_path: List[str]


class SaveState(BaseModel):
    run_id: str
    status: str
    goal: str
    worked: List[str]
    failed: List[str]
    last_good_checkpoint: Optional[str] = None
    blocked_on: str
    recommended_next_actions: List[str]
    context_summary: str
    compress_source: str  # "live" | "fallback" | "fixture"


class RunState(BaseModel):
    run_id: str
    status: RunStatus
    scenario_id: str
    goal: str
    steps: List[AgentStep] = Field(default_factory=list)
    entropy: Optional[EntropyBreakdown] = None
    save_state: Optional[SaveState] = None
    decision_tree: Optional[DecisionTree] = None
    voice_alert_text: Optional[str] = None
    overrides: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


# Request models
class CreateRunRequest(BaseModel):
    scenario_id: str


class StartRunRequest(BaseModel):
    pass


class OverrideRequest(BaseModel):
    """Human control input for fixture or live Vibe runs."""

    choice_id: Optional[str] = Field(default=None, max_length=160)
    rationale: Optional[str] = Field(default=None, max_length=2000)
    # Compatibility path for live Vibe runs only. Fixture runs require choice_id.
    text: Optional[str] = Field(default=None, max_length=2000)



class VibeToolEventRequest(BaseModel):
    """A completed Vibe tool call emitted by the project-local hook adapter."""

    event_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    event_type: str = "post_tool"
    phase: Optional[str] = None
    goal: str = Field(default="Mistral Vibe coding session", max_length=1000)
    tool_name: str = Field(min_length=1, max_length=120)
    tool_call_id: Optional[str] = Field(default=None, max_length=200)
    input_summary: Optional[str] = Field(default=None, max_length=4000)
    output_summary: Optional[str] = Field(default=None, max_length=4000)
    status: str = "ok"
    error_signature: Optional[str] = Field(default=None, max_length=1000)
    files_touched: List[str] = Field(default_factory=list, max_length=100)
    timestamp: Optional[str] = None
