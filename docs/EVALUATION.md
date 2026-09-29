# Evaluation

## Evaluation question

**Does historical memory change what the agent investigates next?**

We intentionally evaluate behavior rather than inventing accuracy percentages.

## Baseline

For the same current incident, Memory OFF must:

- not call Hindsight recall
- produce only generic investigation steps
- contain no historical evidence

## Memory condition

Memory ON must:

- call Hindsight recall
- expose recalled evidence
- identify reusable historical experience
- alter at least one investigation priority when relevant evidence exists
- keep current hypotheses explicitly unconfirmed
- preserve a trace from each changed step to the historical incident evidence

## Failure-memory case

Given a historical action that failed and resembles a baseline action, the baseline action should be marked **DEPRIORITIZED** with a citation to the historical incident.

## Success-memory case

Given a historical successful mitigation, the plan should surface that mitigation conditionally, with a rationale explaining that current evidence must confirm the hypothesis first.

## Generalization test

A separate synthetic incident uses:

- notification latency
- a stuck scheduler
- a failed mail-queue restart
- a successful scheduler restart

The expected behavior is that the system still extracts and uses those lessons without any connection-pool or `INC-1041` rule.

## Negative case

When recall returns no relevant prior experience, the Memory ON plan should collapse to the same generic baseline and explicitly say that no relevant prior experience was found.

## Current test suite

The project tests:

- retain/recall mapping
- duplicate retention behavior
- Memory OFF isolation
- memory-driven plan changes
- failed-action deprioritization
- successful-mitigation surfacing
- unrelated memory filtering
- generic historical incident behavior
- API error conversion
- backend selection and secret-safe settings representation

The live Hindsight round-trip test remains environment-gated and runs when `HINDSIGHT_BASE_URL` is present.
