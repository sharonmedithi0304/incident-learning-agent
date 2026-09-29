"""Extract reusable operational experience from recalled Hindsight memories.

This module intentionally avoids incident-specific/domain-specific rules. It looks for
generic evidence patterns (failed actions, successful mitigations, and root-cause
statements) in whatever text Hindsight returns.
"""
import re
from dataclasses import dataclass, field

from .models import HistoricalAction, Memory

_FAILED = re.compile(
    r"\b(fail(?:ed|ure|s|ing)?|did not|didn't|no improvement|ineffective|unsuccessful|"
    r"not mitigate|not resolve|didn't help)\b", re.I
)
_SUCCESS = re.compile(r"\b(success(?:ful|fully)?|worked|resolved|restored|mitigated|fixed|effective)\b", re.I)
_ROOT = re.compile(r"\b(root cause|actual cause|underlying cause|caused by)\b", re.I)
_MITIGATION = re.compile(
    r"\b(mitigation|mitigated|resolved|restored|fixed|worked|rollback|rolled back|revert(?:ed)?|reverted)\b",
    re.I,
)

@dataclass
class Insight:
    failed_actions: list[Memory] = field(default_factory=list)
    successful_mitigations: list[Memory] = field(default_factory=list)
    root_causes: list[Memory] = field(default_factory=list)

    @property
    def has_any_lesson(self) -> bool:
        return bool(self.failed_actions or self.successful_mitigations or self.root_causes)

def analyze(memories: list[Memory]) -> Insight:
    ins = Insight()
    for m in memories:
        text = m.text or ""
        if _FAILED.search(text):
            ins.failed_actions.append(m)
        if _SUCCESS.search(text) and _MITIGATION.search(text):
            ins.successful_mitigations.append(m)
        if _ROOT.search(text):
            ins.root_causes.append(m)
    return ins

def _extract_after(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = text[m.end():].strip(" :.-'\"")
            if value:
                return value.rstrip(".")
    return text.strip()

def summarize_root_cause(memory: Memory) -> str:
    return _extract_after(
        memory.text or "",
        [
            r"\b(?:root cause|actual cause|underlying cause)\b[^.]{0,100}?\bwas\b",
            r"\bcaused by\b",
        ],
    )

def summarize_mitigation(memory: Memory) -> str:
    text = memory.text or ""
    # Handles both "mitigated by X" and "X successfully mitigated" formulations.
    for pattern in [
        r"\bsuccessful mitigation\b[^.]{0,100}?\bwas to\b",
        r"\b(?:mitigated|resolved|fixed|restored)\b\s+(?:by|when|after)\b",
    ]:
        value = _extract_after(text, [pattern])
        if value != text.strip():
            return value
    m = re.search(r"(?:^|(?:[.;]|\bbut\b)\s+)(?:the\s+)?([^.;]{3,120}?)\s+successfully\s+(?:mitigated|resolved|fixed|restored)\b", text, re.I)
    if m:
        return m.group(1).strip(" :-'")
    value = _extract_after(text, [r"\b(?:rollback|revert(?:ed)?)\b"])
    return value

def summarize_failed_action(memory: Memory) -> str:
    text = memory.text or ""
    quoted = re.search(r"\baction\s+['\"]([^'\"]+)['\"]\s+failed\b", text, re.I)
    if quoted:
        return quoted.group(1).strip()
    attempt = re.search(r"\battempt(?:ed)?\s+to\s+(.+?)\s+(?:failed|did not|didn't)\b", text, re.I)
    if attempt:
        return attempt.group(1).strip(" .")
    gerund = re.search(r"(?:^|(?:[.;]|\bbut\b)\s+)(?:the\s+)?([A-Za-z][A-Za-z0-9 /_-]{2,100}?)\s+failed\s+(?:to\s+)?(?:reduce|resolve|mitigate|fix|improve|restore)\b", text, re.I)
    if gerund:
        return gerund.group(1).strip(" .:-")
    return text.strip()

def _action_key(text: str) -> str:
    normalized = re.sub(r"\bincreasing\b", "increase", text.lower())
    normalized = re.sub(r"\bexpanded\b", "expand", normalized)
    normalized = re.sub(r"\bscaled\b", "scale", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .:-")
    return normalized

def historical_actions(ins: Insight) -> list[HistoricalAction]:
    out: list[HistoricalAction] = []
    seen: set[tuple[str, str]] = set()
    for m in ins.failed_actions:
        desc = summarize_failed_action(m)
        key = ("FAILED", _action_key(desc))
        if key in seen:
            continue
        out.append(HistoricalAction(
            incident_id=m.document_id,
            description=desc,
            outcome="FAILED",
            memory_id=m.id,
        ))
        seen.add(key)
    for m in ins.successful_mitigations:
        desc = summarize_mitigation(m)
        key = ("SUCCESSFUL", _action_key(desc))
        if key in seen:
            continue
        out.append(HistoricalAction(
            incident_id=m.document_id,
            description=desc,
            outcome="SUCCESSFUL",
            memory_id=m.id,
        ))
        seen.add(key)
    return out
