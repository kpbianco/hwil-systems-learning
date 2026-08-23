# P06 — Trace a Command Path

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 2:** Allocation and interfaces  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you trace a Command Path?

## Command-path mental model

P04 defined the functions in a rotary-position transaction, and P05 assigned each function an execution
domain. P06 holds those decisions fixed and traces one logical command through five owned stages:

1. application software captures the operator target;
2. independent hardware validates its authority;
3. application software computes error from a named observation;
4. application software generates a bounded correction; and
5. the hardware-side `Update physical state` input latch receives that correction.

The named observation is an input to this lesson, not a measurement path. The visible calculations inherited
from P04 are

```text
error_deg = accepted_target_deg - observed_position_deg
correction_deg_per_update = response_fraction * error_deg
```

For each adjacent pair, `boundaryCrossed[i]` determines whether the next stage is reached. Therefore
`stageReached[i+1] = boundaryCrossed[i]`, and the reached stages form one contiguous prefix. A value can be
correct at its current owner while the next owner never receives it.

## Learning flow

1. Read how P04 functions and P05 owners become a path rather than a new allocation.
2. Inspect baseline reachability, then trace degree and degree-per-update values without mixing units.
3. Move only the authority limit and observe where an unchanged request stops or advances.
4. Reset, open one ownership boundary at a time, and localize the first missing handoff.
5. Observe cancellation, timeout, and their tie as already-asserted guards at the final handoff.
6. Break the assessment by calling local dispatch endpoint receipt, then recover and run checks.

## Evidence and scope boundaries

- `model.m` — fixed-size, deterministic value, ownership, boundary, guard, and reporting calculation.
- `experiment.m` — complementary baseline views, two isolated sweeps, guarded terminals, and false dispatch-only success.
- `interactive.m` — bounded request, observation, authority, response, boundary, event, evidence, and reset controls.
- `lesson.m` and `lesson.md` — concept-first equations, prerequisite connection, and misconception correction.
- `walkthrough.md` — one observation and mechanism transition at a time.
- `checks.md` and `run_checks.m` — independent equations, limits, malformed inputs, cancellation, timeout, isolation, and teach-back.

`actuatorCommandReceived` means only that an instructional logical value reached the hardware-side input
latch. It is not evidence of electrical signaling, actuator motion, achieved safe hold, or physical response.
The safe-hold outputs are logical requirements and availability flags only. P07 owns the measurement-data
path, P08 owns formal interface contracts and message definitions, and P11 owns elapsed latency, scheduling,
retries, deadlines, and jitter. This module uses no random source, external data, file/network/device I/O,
Simulink model, or toolbox solver.
