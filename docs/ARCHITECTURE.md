# Architecture

## Core contract

The agent separates **retrieval**, **experience extraction**, and **investigation planning**.

### Retrieval

`HindsightStore.recall()` is responsible only for talking to Hindsight and mapping returned memories into the internal `Memory` model.

### Experience extraction

`insight.py` classifies whatever recalled text Hindsight returns into three generic evidence types:

- failed actions
- successful mitigations
- root-cause statements

The classifier is intentionally domain-agnostic. It must not branch on a specific incident ID or one particular technology.

### Planning

`agent.py` keeps a generic baseline and layers recalled experience over it:

- recalled root causes become explicit hypotheses to verify
- successful mitigations become conditional preparation steps
- failed actions are matched against baseline actions and deprioritized when similar
- unmatched failed actions are surfaced as cautions rather than silently discarded

A document-level relevance rule keeps the full incident experience together: if one recalled fact establishes that an incident is relevant, the other facts from the same `document_id` can participate in planning.

## Traceability

Memory-driven `Step` objects carry:

- a human-readable rationale
- evidence IDs mapped to human-readable incident/document IDs

The UI intentionally hides raw memory UUIDs from the primary judge-facing view.

## Two-mode evaluation

```text
Memory OFF
  current incident only
        |
        v
  deterministic baseline

Memory ON
  current incident
        +
  Hindsight recalled experience
        |
        v
  modified investigation
```

The comparison endpoint runs both modes against the same incident so the behavioral difference is explicit.

## External dependency

Hindsight is the persistent memory layer.

The application does not claim that historical evidence proves a current diagnosis. The agent uses memory to prioritize what engineers should verify next.
