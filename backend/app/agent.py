from .config import Settings, load_settings
from .hindsight_store import HindsightStore, build_query
from .insight import analyze, historical_actions
from .llm import polish_why
from .models import Change, Comparison, Investigation, Memory, NewIncident, Step

GENERIC = {
    "deploy": "Review recent deployments and diff config/code changes",
    "logs": "Scan application logs and traces for errors and timeouts",
    "db": "Inspect database CPU, slow queries and locks",
    "deps": "Check downstream dependencies (payments, inventory) for added latency",
    "scale": "Scale up database capacity if the database looks saturated",
}


def _steps(specs: list[tuple]) -> list[Step]:
    return [
        Step(order=i + 1, text=t, source=src, rationale=r, deprioritized=d)
        for i, (t, src, r, d) in enumerate(specs)
    ]


def _cite(ms: list[Memory]) -> str:
    return ", ".join(sorted({m.document_id or m.id for m in ms}))


def investigate(inc: NewIncident, store: HindsightStore, memory: bool, settings: Settings | None = None) -> Investigation:
    settings = settings or load_settings()
    v = inc.deploy_version
    memories: list[Memory] = store.recall(build_query(inc)) if memory else []
    ins = analyze(memories)

    if memory and ins.has_pool_lesson:
        lesson = ins.pool_mitigation + ins.pool_root_cause
        src = _cite(lesson)
        specs = [
            (f"Check connection-pool config and live metrics (in-use vs max, wait time, acquire timeouts) on {inc.service}",
             "memory", f"Root cause of a similar past incident ({src}) was connection-pool exhaustion", False),
            (f"Diff connection-pool settings between the previous release and {v}",
             "memory", f"The past incident ({src}) was tied to a deploy that changed pool config", False),
        ]
        if ins.pool_mitigation:
            specs.append((
                "If the pool is saturated: roll back the connection-pool configuration",
                "memory", f"This mitigation restored normal latency in {_cite(ins.pool_mitigation)}", False))
        specs += [(GENERIC[k], "generic", "", False) for k in ("deploy", "logs", "db", "deps")]
        specs.append((GENERIC["scale"] + " — DEPRIORITIZED", "generic",
                      f"Scaling DB capacity FAILED in {_cite(ins.failed_scaling)}" if ins.failed_scaling
                      else "Not supported by past evidence", bool(ins.failed_scaling)))
        hypothesis = f"Connection-pool exhaustion aggravated by {v} (recalled from {src})"
        why = (
            f"Hindsight recalled {len(memories)} memories from {_cite(memories)}. "
            + (f"Scaling DB capacity FAILED there. " if ins.failed_scaling else "")
            + "The true cause was connection-pool exhaustion, fixed by rolling back the pool configuration. "
            f"This incident shares the checkout-latency-after-deploy pattern, so the plan now checks the pool first, "
            "prepares the known rollback, and demotes DB scaling."
        )
        why = polish_why(why, settings)
    else:
        specs = [(GENERIC[k], "generic", "", False) for k in ("deploy", "db", "scale", "logs", "deps")]
        hypothesis = f"Likely database overload or a regression introduced by {v}"
        why = ("Memory is OFF: the plan uses only the current incident's data." if not memory
               else "No relevant prior experience recalled: plan matches the generic baseline.")

    return Investigation(
        incident_id=inc.id, memory_enabled=memory, memory_backend=store.backend,
        hypothesis=hypothesis, steps=_steps(specs), evidence=memories if memory else [],
        historical_actions=historical_actions(ins), why_changed=why,
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
    return Comparison(off=off, on=on, changes=changes, first_step_changed=off.steps[0].text != on.steps[0].text)
