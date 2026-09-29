# Incident Learning Agent

**Production incident memory that changes the next investigation.**

A focused incident-response agent that turns resolved incidents into reusable operational experience. With Hindsight memory enabled, the next investigation can surface prior root-cause evidence, successful mitigations, and failed actions—and change its investigation priorities accordingly.

## Why this exists

During an incident, engineers are not starting from zero. Teams have already tried things, discovered root causes, and learned which mitigations actually worked.

The failure mode we target is simple:

```text
Past incident -> knowledge is retained -> future incident -> investigation changes
```

The product is deliberately narrow: one workflow, one persona, one visible memory loop.

## The memory loop

1. **Retain** a resolved incident as an atomic narrative containing symptoms, hypotheses, actions, outcomes, root cause, mitigation, and resolution.
2. **Recall** relevant experience from Hindsight for a new incident.
3. **Extract** reusable experience from whatever wording Hindsight returns—without relying on a single incident ID or a single domain storyline.
4. **Change the plan**:
   - historical root-cause hypotheses move earlier as tests to verify
   - successful mitigations are surfaced conditionally
   - previously failed actions can be deprioritized
5. **Explain why** the plan changed and cite the historical incident that supplied the evidence.

Memory changes prioritization; it does not claim a historical cause is proven for the current incident.

## Before vs. after

**Memory OFF**

The agent investigates the current incident from current evidence only.

**Memory ON**

The agent can say, in effect:

> A similar historical experience exists. Its root-cause hypothesis is worth checking first, its successful mitigation is worth preparing if current evidence confirms it, and a previously failed action should not be the first move.

## Architecture

```text
                Browser UI
                    |
                    v
              FastAPI backend
          _________|____________
         |         |            |
    Incident    Planner     HindsightStore
      model        |            |
         |         |            v
         |         +------> Hindsight Cloud
         |                      |
         +----------------------+
                 evidence
```

The planner has two intentional modes:

```text
Memory OFF -> generic baseline

Memory ON
   -> Hindsight recall
   -> document-level relevant experience
   -> root causes / mitigations / failures
   -> traceable investigation changes
```

See `docs/ARCHITECTURE.md` for the implementation details and `docs/EVALUATION.md` for the behavioral evaluation contract.

## Run locally

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example`.

For real Hindsight Cloud:

```env
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=<your-key>
```

Never commit `.env`.

For local-only development, leave `HINDSIGHT_BASE_URL` empty and the app uses the explicit `FAKE MEMORY · LOCAL DEV` backend.

Start:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Open `http://127.0.0.1:8000`.

## Demo flow

1. **Seed historical incident** — retain `INC-1041`.
2. **Memory OFF** — show the generic investigation.
3. **Memory ON** — show recalled evidence changing the investigation.
4. **Compare** — show the before/after plan and the reason for each memory-driven change.

The strongest moment is:

```text
FAILED historical action
        +
SUCCESSFUL historical mitigation
        +
ROOT-CAUSE evidence
        |
        v
different investigation priorities
```

## API

- `GET /api/health`
- `GET /api/scenario`
- `POST /api/seed`
- `POST /api/investigate`
- `POST /api/compare`

`POST /api/investigate` accepts:

```json
{"memory": false}
```

or

```json
{"memory": true}
```

## Safety and failure behavior

- Memory OFF does not call `recall()`.
- When Hindsight is explicitly configured, the app does not silently fall back to fake memory.
- `/api/health` checks the configured Hindsight backend.
- Hindsight errors are surfaced as API errors rather than silently converted into plausible-looking results.
- Historical memory is evidence for investigation, not proof of the current root cause.
- No production action is executed automatically.

## Evaluation principle

We evaluate the memory feature behaviorally, not with invented accuracy numbers:

> Can the same current incident produce a meaningfully different investigation when relevant historical experience is available?

The test suite includes a different historical incident to ensure the memory pipeline is not tied to `INC-1041` or connection-pool terminology.

## Project status

This repository contains a working reference implementation with real Hindsight Cloud integration and a deterministic local fallback for development and testing.
