# P04 — Decompose a System into Functions

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 1:** Mission and behavior  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you decompose a System into Functions?

## Functional mental model

Continue the P03 rotary-position behavior, but open the system boundary into transformations rather than
components. A complete chain captures and preserves operator intent, validates command authority, observes
position, computes signed error, generates a bounded correction, updates the physical state, confirms the
requested behavior, supervises cancellation and deadline, and reports one end-to-end outcome.

The transparent correction law is

```text
position[k+1] = position[k] + response_fraction * (target - position[k])
```

For this decomposition exercise, completion uses a visible position-only proxy: original request error must
remain within tolerance for a declared number of consecutive 20-millisecond instructional updates. It does
not replace P03's position-plus-velocity sustained-settling contract or claim plant fidelity. These are
logical function contracts only: P05 decides how functions are allocated across hardware and software,
while P06 and P07 later trace their interfaces in detail; the fixed update is not a path-latency budget.

## Learning flow

1. Read how P03's desired behavior becomes named function inputs and outputs.
2. Inspect the deterministic position result, then the complementary function-activation view.
3. Sweep correction response fraction and observe how one function changes convergence time.
4. Reset, sweep confirmation depth, and separate physical entry from evidence time.
5. Omit validation, request 70 degrees against 45 degrees of authority, and diagnose false success.
6. Exercise rejection, timeout, cancellation, recovery, and limits before a two-sentence teach-back.

## Artifact map and dependencies

- `model.m` — fixed-size, deterministic, presentation-free function-chain calculation and contracts.
- `experiment.m` — baseline views, two isolated sweeps, and one missing-validation case.
- `interactive.m` — bounded request, correction, evidence, authority, deadline, cancellation, and mode controls.
- `lesson.m` and `lesson.md` — concept-first narrative with visible equations and prerequisite boundary.
- `walkthrough.md` — one observation and mechanism transition at a time.
- `checks.md` and `run_checks.m` — independent limits, failure paths, compatibility, isolation, and teach-back.

The implementation uses base MATLAB operations and no toolbox, external data, random source, device,
network, or file I/O. Retained batch evidence is static unless a separately named MATLAB environment runs
the scripts; UI, numerical-fidelity, bench, HIL, and field validation are not implied.
