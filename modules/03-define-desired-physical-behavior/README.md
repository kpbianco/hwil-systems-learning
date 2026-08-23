# P03 — Define Desired Physical Behavior

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 1:** Mission and behavior  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you define Desired Physical Behavior?

## Physical mental model

A rotary test article receives an accepted position command at time zero. Its transparent second-order
response exposes position in degrees and velocity in degrees per second. Desired behavior is more than
“it moves”: the request must be inside command authority, preserve direction, and enter and remain inside
both position and velocity tolerances by a named deadline.

## Learning flow

1. Read the physical behavior envelope inherited from the P02 operator transaction.
2. Inspect the deterministic position baseline, then its complementary velocity view.
3. Sweep command magnitude and observe position and speed scale together.
4. Reset, sweep damping ratio, and observe overshoot and sustained settling change.
5. Request an angle outside command authority and distinguish physical settling from requested success.
6. Run independent limits and failure checks, answer interpretation questions, and teach back the contract.

## Artifact map

- `model.m` — fixed-size, deterministic, presentation-free response and behavior metrics.
- `experiment.m` — baseline views, two isolated parameter sweeps, and the broken input-envelope case.
- `interactive.m` — bounded controls for command, damping, response frequency, authority, and deadline.
- `lesson.m` and `lesson.md` — concept-first tutor narrative and visible equations.
- `walkthrough.md` — one observation and mechanism transition at a time.
- `checks.md` and `run_checks.m` — interpretation, limiting cases, malformed inputs, recovery, and bounds.

## Dependencies and evidence boundary

The implementation uses base MATLAB operations and no toolbox, external data, random source, device,
network, or file I/O. The retained batch evidence establishes static source and contract checks only;
MATLAB-runtime, UI, numerical-fidelity, bench, HIL, and field validation require separate evidence.
