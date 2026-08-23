# P05 — Allocate Functions Across Hardware and Software

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 2:** Allocation and interfaces  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you allocate Functions Across Hardware and Software?

## Allocation mental model

P04 named ten functions without choosing components. P05 preserves those contracts and gives each function
exactly one owner: application software or independent hardware logic. Fixed sensor and actuation endpoints
stay in hardware; request, confirmation, and reporting boundaries stay in software; the learner allocates
the control pair and the validation/cancellation/deadline supervision group.

The transparent resource calculation is

```text
software demand = sum(software work for software-owned functions)
hardware demand = sum(hardware allocation for hardware-owned functions)
domain margin   = declared capacity - domain demand
```

An allocation is acceptable only when both domains fit, fixed bindings remain valid, supervision is outside
the application-software fault it must contain, and the injected boundary event is handled. A function is
called available only when its owner domain fits and, for software, the application is not stalled. Work units
per update and hardware allocation units are instructional design quantities, not execution times, WCET, link
latency, jitter, silicon utilization, or proof of a real implementation.

## Learning flow

1. Read how the P04 function contracts become explicit domain owners.
2. Inspect the baseline owner map, then the complementary resource-utilization view.
3. Move the control pair from software to hardware and observe demand transfer between domains.
4. Reset, move supervision from hardware to software, and inject an application-software stall plus cancellation.
5. Break the assessment by checking resource fit only; diagnose the false allocation approval.
6. Exercise capacity limits, cancellation, deadline/timeout, recovery, and checks before a two-sentence teach-back.

## Artifact map and boundaries

- `model.m` — fixed-size, deterministic ownership, resource, availability, and decision calculation.
- `experiment.m` — two complementary baseline views, two isolated owner sweeps, and one false-approval case.
- `interactive.m` — bounded owner, capacity, software-state, event, assessment, and reset controls.
- `lesson.m` and `lesson.md` — concept-first equations, fault-domain reasoning, and prerequisite connection.
- `walkthrough.md` — one observation and mechanism transition at a time.
- `checks.md` and `run_checks.m` — independent sums, limits, malformed inputs, containment, isolation, and teach-back.

P06 later traces command delivery, P07 traces measurement transformations, and P11 owns latency, scheduling,
and jitter budgets. P05 injects cancellation and deadline/timeout only at a named function boundary; it does
not model event routing or temporal precedence. The implementation uses base MATLAB operations and no random
source, external data, toolbox solver, device, network, or file I/O. A logical safe-hold request being
available is not evidence that physical safe hold was commanded or achieved.
