"""Thin wrapper over Hindsight. Uses only APIs verified in hindsight-client 0.10.1:
  Hindsight(base_url, api_key), create_bank(bank_id, name, mission),
  retain(bank_id, content, context, document_id, tags, metadata),
  recall(bank_id, query, max_tokens, budget) -> .results[*].{id,text,type,context,document_id,tags}
"""
import logging

from .config import Settings
from .fake_hindsight import FakeHindsight
from .models import Incident, Memory, NewIncident

log = logging.getLogger(__name__)

BANK_MISSION = (
    "Remember production incident experience: symptoms, hypotheses, which actions FAILED, "
    "which mitigations SUCCEEDED, and true root causes, so future investigations can reuse them."
)


def incident_to_narrative(inc: Incident) -> str:
    """Self-contained, atomic sentences (each names the incident) so extracted facts stay meaningful."""
    s = [f"Incident {inc.id}: {inc.symptom} ({inc.latency_s}s) in {inc.service} after deploy {inc.deploy_version}."]
    if inc.initial_hypothesis:
        s.append(f"In {inc.id} the initial hypothesis for the {inc.service} latency was {inc.initial_hypothesis}.")
    for a in inc.actions:
        note = f" — {a.note.rstrip('.')}" if a.note else ""
        s.append(f"In {inc.id} the action '{a.description}' {a.outcome}{note}.")
    if inc.root_cause:
        s.append(f"The actual root cause of {inc.id} {inc.service} latency was {inc.root_cause}.")
    if inc.successful_mitigation:
        s.append(f"The successful mitigation for {inc.id} {inc.service} latency was to {inc.successful_mitigation}.")
    if inc.resolution:
        s.append(f"In {inc.id}, {inc.resolution}.")
    return " ".join(x if x.endswith((".", "!", "?")) else x + "." for x in s)


def build_query(inc: NewIncident) -> str:
    signals = "; ".join(inc.signals)
    return (
        f"{inc.service} {inc.symptom} after deploy {inc.deploy_version}. {signals}. "
        "Prior incidents with similar latency symptoms: which fixes failed and which mitigations worked?"
    )


class HindsightStore:
    def __init__(self, client, bank_id: str, backend: str):
        self.client = client
        self.bank_id = bank_id
        self.backend = backend  # "hindsight" | "fake"

    def ensure_bank(self) -> None:
        try:
            self.client.create_bank(bank_id=self.bank_id, name="Incident Learning Agent", mission=BANK_MISSION)
        except Exception as e:  # bank may already exist / be managed elsewhere
            log.warning("create_bank skipped: %s", type(e).__name__)

    def retain_incident(self, inc: Incident) -> str:
        content = incident_to_narrative(inc)
        self.client.retain(
            bank_id=self.bank_id,
            content=content,
            context="production incident postmortem: failed and successful actions",
            document_id=inc.id,
            tags=["incident", inc.service, "postmortem"],
            metadata={"incident_id": inc.id, "service": inc.service, "deploy_version": inc.deploy_version},
        )
        return content

    def recall(self, query: str) -> list[Memory]:
        resp = self.client.recall(bank_id=self.bank_id, query=query, max_tokens=2048, budget="mid")
        return [
            Memory(
                id=str(r.id), text=r.text, type=getattr(r, "type", None),
                document_id=getattr(r, "document_id", None),
                tags=list(getattr(r, "tags", None) or []), context=getattr(r, "context", None),
            )
            for r in resp.results
        ]


def build_store(settings: Settings) -> HindsightStore:
    if settings.use_real_hindsight:
        from hindsight_client import Hindsight  # real client

        client = Hindsight(base_url=settings.hindsight_base_url, api_key=settings.hindsight_api_key or None)
        return HindsightStore(client, settings.hindsight_bank_id, "hindsight")
    return HindsightStore(FakeHindsight(), settings.hindsight_bank_id, "fake")
