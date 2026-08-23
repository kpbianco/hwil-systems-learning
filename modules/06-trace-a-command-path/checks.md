# Checks: Trace a Command Path

## Observation and interpretation questions

Answer one question after the corresponding view:

1. Which P04 functions and P05 owners form this five-stage command path?
2. Why does the lesson separate degrees from degrees per update?
3. At an authority limit of exactly 30 deg, why does the 30 deg request advance?
4. When `B3` is open, which local value exists and which downstream owner never receives it?
5. How does a contiguous reached-stage prefix localize the first missing handoff?
6. Why are cancellation and timeout guards rather than serial processing stages?
7. What does cancellation win in the injected cancellation/timeout tie, and what timing fact remains unknown?
8. Why can `traceContractMet` be true for a rejected or cancelled transaction while command delivery is false?
9. Which evidence does the broken dispatch-only assessment substitute for endpoint receipt?
10. Why do endpoint receipt and a logical safe-hold request prove neither physical motion nor achieved safety?

## Independent, negative, and recovery checks

`run_checks.m` independently reconstructs the baseline value equations and verifies stage/owner/unit identity,
the fixed five-stage/four-boundary resource envelope, the reachability recurrence, every open-boundary location,
authority below/equal/above limits, positive and negative commands, zero error, zero/full response, maximum
bounded angles, cancellation, timeout, cancellation/timeout precedence, unreachable guards, validation-before-
event behavior, final-guard precedence, complete versus broken reporting, compatible scalar inputs, malformed
numeric and categorical inputs, call isolation, and exact recovery.

The timeout is an injected logical event with no elapsed-time value. The checks do not run a communication
protocol, measurement chain, plant, scheduler, physical actuator, or safe-hold mechanism. Repository Python
tests execute an independently written oracle and static source checks; they do not execute MATLAB.

Rollback is a source-and-manifest operation. The durable Python fixture rolls P06 and every later module back
inside an isolated copy, then proves persisted P06 progress recovers to implemented P05. It never changes the
real learner state or worktree during validation.

## Executable check

Run in MATLAB:

```matlab
run_checks
```

All assertions must pass before learner completion. Static checks cannot substitute for execution in a named
licensed MATLAB runtime.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you trace a Command
Path?” State the handoff/value mechanism first and the system consequence second.
