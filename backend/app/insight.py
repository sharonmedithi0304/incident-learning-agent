"""Classify recalled memories. Wording from a real Hindsight server may be paraphrased,
so we match on meaning-bearing keywords, not exact strings."""
import re
from dataclasses import dataclass, field

from .models import HistoricalAction, Memory

_FAIL = re.compile(r"\b(fail\w*|did not|didn't|no improvement|ineffective|unsuccessful)\b", re.I)
_SCALE = re.compile(r"\b(scal\w*|capacity)\b", re.I)
_POOL = re.compile(r"connection[- ]pool", re.I)
_FIX = re.compile(r"\b(roll(ed)? ?back|rollback|revert\w*)\b", re.I)
_ROOT = re.compile(r"\b(root cause|actual cause|exhaust\w*)\b", re.I)


@dataclass
class Insight:
    failed_scaling: list[Memory] = field(default_factory=list)
    pool_mitigation: list[Memory] = field(default_factory=list)
    pool_root_cause: list[Memory] = field(default_factory=list)

    @property
    def has_pool_lesson(self) -> bool:
        return bool(self.pool_mitigation or self.pool_root_cause)


def analyze(memories: list[Memory]) -> Insight:
    ins = Insight()
    for m in memories:
        t = m.text
        if _SCALE.search(t) and _FAIL.search(t):
            ins.failed_scaling.append(m)
        if _POOL.search(t) and _FIX.search(t):
            ins.pool_mitigation.append(m)
        if _POOL.search(t) and _ROOT.search(t):
            ins.pool_root_cause.append(m)
    return ins


def historical_actions(ins: Insight) -> list[HistoricalAction]:
    out, seen = [], set()
    for m in ins.failed_scaling:
        out.append(HistoricalAction(incident_id=m.document_id, description=m.text, outcome="FAILED", memory_id=m.id))
        seen.add(m.id)
    for m in ins.pool_mitigation:
        if m.id not in seen:
            out.append(HistoricalAction(incident_id=m.document_id, description=m.text, outcome="SUCCESSFUL", memory_id=m.id))
    return out
