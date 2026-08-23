# Lesson: Trace a Command Path

## Guiding question

What inputs, observable effects, and failure modes matter when you trace a Command Path?

## From allocation to handoffs

P04 answered “what functions exist?” and P05 answered “which domain owns each function?” A command-path
trace asks a different question: “which owner actually received which value?” Keep P05’s baseline allocation
fixed while following a single rotary command:

| Stage | P04/P06 responsibility | P05 owner carried forward | Output unit |
| --- | --- | --- | --- |
| 1 | Capture intent | application software | deg |
| 2 | Validate authority | independent hardware supervision | deg |
| 3 | Compute error | application software control | deg |
| 4 | Generate correction | application software control | deg/update |
| 5 | `Update physical state` input latch | hardware interface | deg/update |

The final label says **input latch** deliberately. P06 stops at logical receipt of the correction by the
hardware-side endpoint; it does not execute `Update physical state` or claim a physical result.

## Value lineage and reachability

The inherited P04 baseline is a 30 deg request, a 45 deg symmetric authority limit, an observation of 0 deg,
and response fraction 0.35. The transparent lineage is

```text
accepted target = 30 deg
error           = 30 deg - 0 deg = 30 deg
correction      = 0.35 * 30 deg = 10.5 deg/update
```

Do not put all five values on one unqualified axis: stages 1–3 use degrees, while stages 4–5 use degrees per
update. The experiment separates those views.

For boundaries `B1` through `B4`, the routing recurrence is

```text
stageReached[1]   = true
stageReached[i+1] = boundaryCrossed[i]
```

A boundary is crossed only if its source stage is reached, the boundary is not declared open, and any local
guard permits the crossing. This makes reachability a contiguous prefix. The first absent crossing identifies
where to look; it does not by itself explain why the boundary was unavailable.

## Lever 1 — authority limit

Hold the request at 30 deg and move only the symmetric authority limit. At 20 deg, the path reaches
`Validate authority` and stops. At 30 deg, equality passes because the rule is
`abs(requestedAngleDeg) <= authorityLimitDeg`; the correction then reaches the endpoint. The request itself,
observation, response fraction, owners, and boundaries do not change.

An authority rejection is a handled terminal outcome, not a delivered command. It raises a logical
`safeHoldRequired` flag and makes a logical safe-hold request available at the independent supervisory owner.
Neither flag proves a physical inhibit or safe state.

## Lever 2 — open boundary

Reset the authority limit, then open one ownership handoff at a time. Opening `B1` leaves only Capture intent
reached; opening `B2`, `B3`, or `B4` leaves exactly two, three, or four stages reached. Local calculations before
the open boundary remain valid. That distinction is the point: correct local output is not delivery evidence.

Boundary names identify ownership handoffs only. P06 does not define a packet schema, units contract, checksum,
wire format, protocol, electrical interface, or retry policy; P08 owns formal interface-control contracts.

## Cancellation, timeout, and precedence

Cancellation and timeout are exogenous logical inputs already asserted when the command reaches the final
handoff guard. They are not serial path stages and carry no milliseconds. Either guard stops the correction
before the actuator input latch, records a handled terminal, and raises the logical safe-hold requirement.

The combined cancellation/timeout input preserves P04’s cancellation precedence and reports `cancelled`.
Authority validation occurs earlier in this bounded path, so an invalid request is rejected before the final
guard is reachable. If an earlier boundary is open, the event is not called observed because its guard never
sees the command. P11 later owns actual elapsed deadlines, scheduling, retry timing, and jitter.

## Deliberately broken evidence boundary

With the final `correction-to-actuator` boundary open, `Generate correction` still produces 10.5 deg/update and
local dispatch is visible. The complete assessment asks whether the actuator input latch received that value
and correctly reports failure. The broken `dispatch-only` assessment reports success from the upstream fact,
creating `falseSuccess = reportedSuccess AND NOT actuatorCommandReceived`.

This is the command-path version of “send is not receive.” Endpoint receipt still is not physical motion.

## Inputs, observables, terminals, and failure modes

- Inputs: requested and observed angle, authority limit, response fraction, selected open boundary, injected
  terminal event, and assessment evidence mode.
- Observable effects: stage reachability and output values, boundary attempted/crossed/open state, authority
  margin, error, correction, event observation, safe-hold requirement, local dispatch, endpoint receipt,
  terminal status, complete truth, reported success, and false success.
- Handled non-delivery terminals: authority rejection, cancellation, and timeout. These meet the trace’s
  terminal-handling contract but are never called command delivery.
- Failures: an open ownership handoff and dispatch-only false success. Malformed and out-of-envelope inputs are
  rejected before any trace is produced.
- Recovery: the model has no persistent or global state; a fresh valid call after a broken boundary, guarded
  terminal, bad assessment, or malformed input reproduces the baseline exactly.

## Common mistakes and future boundaries

- Reached is not the same as correct, and correct local output is not the same as received downstream.
- `traceContractMet` includes a trustworthy handled terminal; `actuatorCommandReceived` alone means delivery.
- A safe-hold requirement is an output requirement, not evidence that a hold command traveled or took effect.
- The observation is a named input. P07 will trace how measurement data is acquired, transformed, qualified,
  and delivered.
- The boundary labels are not interface-control contracts. P08 will define those contracts.
- A timeout event here is a Boolean guard input. P11 will establish time, latency, scheduling, and jitter evidence.
- The endpoint latch is not the plant. Physical execution and confirmation require separately retained evidence.

## Completion standard

Localize an authority stop and an open boundary from the views, distinguish handled terminal outcome from
successful command delivery, diagnose dispatch-only false success, pass `run_checks.m`, and give a two-sentence
teach-back: trace mechanism first, system consequence second.
