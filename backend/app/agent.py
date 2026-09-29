import re

from .config import Settings, load_settings
from .hindsight_store import HindsightStore, build_query
from .insight import analyze, historical_actions, summarize_failed_action, summarize_mitigation, summarize_root_cause
from .models import Change, Comparison, Investigation, Memory, NewIncident, Step

GENERIC = {
    "deploy": "Review recent deployments and diff config/code changes",
    "logs": "Scan application logs and traces for errors and timeouts",
    "db": "Inspect database CPU, slow queries and locks",
    "deps": "Check downstream dependencies (payments, inventory) for added latency",
    "scale": "Scale up database capacity if the database looks saturated",
}

_STOP = {
    "the", "a", "an", "of", "to", "in", "and", "or", "was", "were", "is", "for", "with",
    "after", "that", "which", "what", "this", "prior", "incident", "incidents", "similar",
    "from", "into", "than", "then", "when", "had", "has", "have", "are", "did", "not",
    "on", "by", "as", "at", "it", "its", "our", "we", "their", "there",
}

def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w.rstrip("s") for w in words if len(w) > 2 and w not in _STOP}

def _incident_tokens(inc: NewIncident) -> set[str]:
    return _tokens(" ".join([inc.service, inc.symptom, inc.title, inc.deploy_version, *inc.signals]))

def _relevance(inc: NewIncident, memory: Memory) -> int:
    return len(_incident_tokens(inc) & _tokens(memory.text or ""))

def _source_label(memory: Memory) -> str:
    if memory.document_id:
        return memory.document_id
    ids = re.findall(r"\bINC-\d+\b", memory.text or "")
    if ids:
        return ids[0]
    return "historical evidence"

def _cite(ms: list[Memory]) -> str:
    return ", ".join(sorted({_source_label(m) for m in ms}))

def _steps(specs: list[tuple]) -> list[Step]:
    return [
        Step(order=i + 1, text=t, source=src, rationale=r, deprioritized=d, evidence_ids=evidence)
        for i, (t, src, r, d, evidence) in enumerate(specs)
    ]

_ALIASES = {
    "db": "database",
    "databases": "database",
    "database": "database",
    "scale": "scale",
    "scaled": "scale",
    "scaling": "scale",
    "increase": "scale",
    "increased": "scale",
    "expand": "scale",
    "expanded": "scale",
    "up": "scale",
    "deployment": "deploy",
    "deployed": "deploy",
    "deploy": "deploy",
    "logs": "logs",
    "logging": "logs",
    "log": "logs",
    "dependency": "dependency",
    "dependencies": "dependency",
    "downstream": "dependency",
    "check": "inspect",
    "inspect": "inspect",
    "review": "inspect",
    "reviewing": "inspect",
}

def _canonical_tokens(text: str) -> set[str]:
    return {_ALIASES.get(token, token) for token in _tokens(text)}

def _overlap(a: str, b: str) -> int:
    return len(_canonical_tokens(a) & _canonical_tokens(b))

def _build_memory_specs(inc: NewIncident, memories: list[Memory]):
    insight = analyze(memories)
    specs = []
    matched_failed_ids: set[str] = set()
    reasons: list[str] = []

    seen_causes: set[str] = set()
    seen_mitigations: set[str] = set()
    for m in insight.root_causes:
        cause = summarize_root_cause(m)
        cause_key = re.sub(r"\s+", " ", cause.lower()).strip(" .")
        if cause_key in seen_causes:
            continue
        seen_causes.add(cause_key)
        src = _cite([m])
        specs.append((
            f"Test the recalled root-cause hypothesis on {inc.service}: {cause}",
            "memory",
            f"Recalled from {src}: historical root-cause evidence; unconfirmed for the current incident.",
            False,
            [src],
        ))
        reasons.append(f"historical root cause: {cause} ({src})")

    for m in insight.successful_mitigations:
        mitigation = summarize_mitigation(m)
        mitigation_key = re.sub(r"\s+", " ", mitigation.lower()).strip(" .")
        if mitigation_key in seen_mitigations:
            continue
        seen_mitigations.add(mitigation_key)
        src = _cite([m])
        specs.append((
            f"If that hypothesis is confirmed, prepare the mitigation that worked before: {mitigation}",
            "memory",
            f"Recorded as successful in {src}; verify current evidence before applying it.",
            False,
            [src],
        ))
        reasons.append(f"successful prior mitigation: {mitigation} ({src})")

    failed_descriptions = []
    seen_failed: set[str] = set()
    for m in insight.failed_actions:
        action = summarize_failed_action(m)
        key = re.sub(r"\bincreasing\b", "increase", action.lower())
        key = re.sub(r"\s+", " ", key).strip(" .:-")
        if key in seen_failed:
            continue
        seen_failed.add(key)
        failed_descriptions.append((m, action))
    demoted = []
    for key in ("deploy", "db", "scale", "logs", "deps"):
        text = GENERIC[key]
        matched = [(m, action) for m, action in failed_descriptions if _overlap(text, action) >= 2]
        if matched:
            best_m, action = max(matched, key=lambda x: _overlap(text, x[1]))
            src = _cite([best_m])
            specs.append((
                text + " — DEPRIORITIZED",
                "generic",
                f"Similar action '{action}' FAILED in {src}.",
                True,
                [src],
            ))
            demoted.append((text, action, src))
            matched_failed_ids.add(best_m.id)
        else:
            specs.append((text, "generic", "", False, []))

    for m, action in failed_descriptions:
        if m.id not in matched_failed_ids:
            src = _cite([m])
            specs.append((
                f"Avoid repeating this failed historical action unless new evidence justifies it: {action}",
                "memory",
                f"This action FAILED in {src}. Treat the historical outcome as a caution, not proof about the current incident.",
                False,
                [src],
            ))
            reasons.append(f"failed prior action: {action} ({src})")

    for _, action, src in demoted:
        reasons.append(f"deprioritized failed action: {action} ({src})")

    unique_reasons = list(dict.fromkeys(reasons))[:6]
    why = (
        f"Hindsight recalled {len(memories)} relevant memories. "
        + ("; ".join(unique_reasons) if unique_reasons else "No reusable prior experience was extracted.")
        + ". Historical evidence is unconfirmed for the current incident. "
        + "Current-incident evidence has not confirmed these historical lessons, "
        "so memory changes investigation priorities but does not declare the current root cause proven."
    )
    return specs, why

def investigate(inc: NewIncident, store: HindsightStore, memory: bool, settings: Settings | None = None) -> Investigation:
    settings = settings or load_settings()
    memories = store.recall(build_query(inc)) if memory else []

    directly_relevant = [m for m in memories if _relevance(inc, m) >= 2]
    relevant_docs = {m.document_id for m in directly_relevant if m.document_id}
    relevant = [
        m for m in memories
        if (m.document_id in relevant_docs) or (_relevance(inc, m) >= 2)
    ]
    if memories and not relevant:
        relevant = memories[:8]

    if memory and relevant:
        specs, why = _build_memory_specs(inc, relevant)
        insight = analyze(relevant)
        if insight.root_causes:
            root = summarize_root_cause(insight.root_causes[0])
            src = _cite(insight.root_causes)
            hypothesis = (
                f"Leading hypothesis: {root} (recalled from {src}) — "
                "unconfirmed against current incident evidence."
            )
        else:
            hypothesis = (
                "Leading hypotheses are informed by recalled prior experience; "
                "current evidence still needs to confirm the cause."
            )
    else:
        specs = [(GENERIC[k], "generic", "", False, []) for k in ("deploy", "db", "scale", "logs", "deps")]
        hypothesis = f"Likely database overload or a regression introduced by {inc.deploy_version}"
        why = (
            "Memory is OFF: the plan uses only the current incident's data."
            if not memory else "No relevant prior experience recalled: plan matches the generic baseline."
        )
        relevant = []

    return Investigation(
        incident_id=inc.id,
        memory_enabled=memory,
        memory_backend=store.backend,
        hypothesis=hypothesis,
        steps=_steps(specs),
        evidence=relevant if memory else [],
        historical_actions=historical_actions(analyze(relevant)) if memory else [],
        why_changed=why,
    )

def compare(inc: NewIncident, store: HindsightStore, settings: Settings | None = None) -> Comparison:
    off = investigate(inc, store, memory=False, settings=settings)
    on = investigate(inc, store, memory=True, settings=settings)
    changes = []
    for s in on.steps:
        if s.source == "memory":
            changes.append(Change(kind="added", text=s.text))
        elif s.deprioritized:
            changes.append(Change(kind="demoted", text=s.text))
    return Comparison(
        off=off,
        on=on,
        changes=changes,
        first_step_changed=off.steps[0].text != on.steps[0].text,
    )
