# Checks: Define Desired Physical Behavior

## Observation questions

Answer one at a time after observing the corresponding view:

1. Why must the baseline satisfy both a position band in degrees and a velocity band in degrees per second?
2. When command magnitude increases inside the valid envelope, what scales and what normalized metric stays fixed?
3. How does damping change overshoot, and why is first entry into the position band not enough to claim settling?
4. In the broken case, how can the article settle physically while the requested behavior remains unmet?
5. What does a negative command test that a magnitude-only requirement would miss?
6. Why does shortening only the deadline change pass/fail without changing the position trajectory?

## Independent and failure checks

`run_checks.m` compares baseline overshoot with the analytic second-order result, verifies sustained
position-plus-velocity settling, covers zero and critical-damping limits, signed symmetry, exact command
authority, an exact deadline tie and one-sample miss, near-critical continuity, a finite-horizon trap, the
broken authority case, compatible numeric scalar classes, malformed inputs, fixed resource bounds,
recovery, and call isolation.

Cancellation is intentionally owned by the prerequisite P02 operator transaction. P03 begins at accepted
physical command time and checks response-deadline failure rather than duplicating transaction cancellation.

## Executable check

Run in MATLAB:

```matlab
run_checks
```

All assertions must pass before learner completion. Repository static checks do not substitute for this
MATLAB-runtime check.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you define
Desired Physical Behavior?” State the physical mechanism first and the operator or design consequence second.
