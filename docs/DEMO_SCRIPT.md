# Demo Script

## 0:00 — Problem

Production incidents generate hard-won knowledge:

- what we suspected
- what we tried
- what failed
- what actually fixed the problem

A one-shot incident agent sees today's telemetry. This project asks whether it can also use yesterday's experience.

## 0:20 — Seed memory

Click **Seed historical incident**.

Say:

> "This stores INC-1041 in Hindsight: the initial database-scaling approach failed, the actual root cause was connection-pool exhaustion, and a rollback resolved the incident."

## 0:45 — Memory OFF

Click **Investigate · Memory OFF**.

Say:

> "Without historical memory, the agent starts with a generic incident investigation."

Point at the generic database/scaling steps.

## 1:15 — Memory ON

Click **Investigate · Memory ON**.

Say:

> "Now the same incident is investigated with Hindsight recall."

Show:

- recalled root-cause evidence
- failed historical action
- successful mitigation
- `FROM MEMORY` steps
- the `DEPRIORITIZED` action

## 1:45 — The proof

Point at the first-step change.

Say:

> "This is the important part: memory didn't just add context. It changed what the agent investigates first."

Then point at the uncertainty wording:

> "The historical root cause is an unconfirmed hypothesis for the current incident. It still has to be verified against current telemetry."

## 2:15 — Compare

Click **Compare**.

Show the Memory OFF and Memory ON plans side by side.

## 2:40 — Close

Say:

> "The goal is not an autonomous production fixer. The goal is an incident-response assistant that preserves organizational experience and uses it to change the next investigation."
