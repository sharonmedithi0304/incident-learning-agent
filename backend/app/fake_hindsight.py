"""LOCAL DEVELOPMENT ONLY — in-memory stand-in for the Hindsight client.

It mimics the *shape* of the real `hindsight_client.Hindsight` methods we use
(create_bank / retain / recall) so the rest of the app has a single code path.
It is NOT Hindsight: it splits retained text into sentence "facts" and ranks by
naive token overlap. The UI/API label it as backend="fake".
"""
import re
from types import SimpleNamespace
from typing import Optional

_STOP = {
    "the", "a", "an", "of", "to", "in", "and", "or", "was", "were", "is", "for", "with",
    "after", "that", "which", "what", "this", "prior", "incident", "incidents", "similar",
    "from", "into", "than", "then", "when", "had", "has", "have", "are", "did", "not",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w.rstrip("s") for w in words if len(w) > 2 and w not in _STOP}


class FakeHindsight:
    def __init__(self) -> None:
        self._facts: list[SimpleNamespace] = []
        self._n = 0

    def create_bank(self, bank_id: str, **kwargs):
        return SimpleNamespace(bank_id=bank_id)

    def retain(
        self,
        bank_id: str,
        content: str,
        context: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
        document_id: Optional[str] = None,
        **kwargs,
    ):
        if document_id:  # re-retaining the same document replaces it
            self._facts = [f for f in self._facts if f.document_id != document_id]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
        for s in sentences:
            self._n += 1
            self._facts.append(
                SimpleNamespace(
                    id=f"fake-{self._n}", bank_id=bank_id, text=s, type="world",
                    context=context, document_id=document_id, tags=list(tags or []),
                    metadata=dict(metadata or {}),
                )
            )
        return SimpleNamespace(success=True, bank_id=bank_id, items_count=1)

    def recall(self, bank_id: str, query: str, max_tokens: int = 4096, budget: str = "mid", **kwargs):
        q = _tokens(query)
        scored = []
        for f in self._facts:
            if f.bank_id != bank_id:
                continue
            score = len(q & _tokens(f.text))
            if score >= 3:
                scored.append((score, f))
        scored.sort(key=lambda t: -t[0])
        return SimpleNamespace(results=[f for _, f in scored[:12]])
