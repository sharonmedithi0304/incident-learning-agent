from typing import Literal, Optional

from pydantic import BaseModel, Field

Outcome = Literal["FAILED", "SUCCESSFUL", "NEUTRAL"]


class Action(BaseModel):
    description: str
    outcome: Outcome
    note: str = ""


class NewIncident(BaseModel):
    """An incident being investigated right now (no resolution yet)."""

    id: str
    title: str
    service: str
    symptom: str
    latency_s: float
    deploy_version: str
    signals: list[str] = Field(default_factory=list)


class Incident(NewIncident):
    """A closed incident with its full learning record (what gets retained)."""

    initial_hypothesis: str = ""
    actions: list[Action] = Field(default_factory=list)
    root_cause: str = ""
    successful_mitigation: str = ""
    resolution: str = ""


class Memory(BaseModel):
    id: str
    text: str
    type: Optional[str] = None
    document_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    context: Optional[str] = None


class Step(BaseModel):
    order: int
    text: str
    source: Literal["generic", "memory"]
    rationale: str = ""
    deprioritized: bool = False


class HistoricalAction(BaseModel):
    incident_id: Optional[str]
    description: str
    outcome: Outcome
    memory_id: str


class Investigation(BaseModel):
    incident_id: str
    memory_enabled: bool
    memory_backend: str
    hypothesis: str
    steps: list[Step]
    evidence: list[Memory] = Field(default_factory=list)
    historical_actions: list[HistoricalAction] = Field(default_factory=list)
    why_changed: str = ""


class Change(BaseModel):
    kind: Literal["added", "demoted"]
    text: str


class Comparison(BaseModel):
    off: Investigation
    on: Investigation
    changes: list[Change]
    first_step_changed: bool
