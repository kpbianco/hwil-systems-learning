# Checks: Allocate Functions Across Hardware and Software

## Observation questions

Answer these interpretation questions one at a time after observing the corresponding view:

1. Which two P04 functions are fixed to physical hardware endpoints, and why?
2. When the control pair moves to hardware, which two demand totals change and which function contracts stay unchanged?
3. Why can an allocation with positive software and hardware margins still be unacceptable?
4. Which three functions form supervision, and which application-software fault must they remain independent from?
5. During a software stall, what does hardware-owned cancellation or deadline supervision make available?
6. Why is a logical safe-hold request not evidence that a physical safe hold was commanded or achieved?
7. Which fact does the broken resource-only assessment omit when it reports false feasibility?
8. Why are work/allocation units intentionally not milliseconds, path latency, scheduling, or jitter evidence?

## Independent, negative, and recovery checks

`run_checks.m` independently sums the visible cost vectors and checks all four control/supervision owner
combinations, exact-capacity and just-below-capacity limits, zero capacities, fixed bindings, one-owner
completeness, cancellation and deadline/timeout containment, event handling under owner-domain overload,
software common-mode loss, false resource-only approval, compatible numeric and text inputs, malformed
categories and capacities, the fixed resource bound, recovery after errors, and call isolation. It also proves
that software state, injected event, and assessment mode cannot mutate the underlying owner map or nominal costs.

Cancellation and deadline are injected at their P04 function boundary. These checks do not simulate event
routing, time ordering, a cancellation/deadline tie, or achieved safe behavior. P04 retains terminal
precedence, P06/P07 retain path detail, and P11 retains timing and jitter.

Rollback is a source-and-manifest operation. The durable Python fixture rolls P05 and all later modules back
inside an isolated copy, then proves that persisted P05 progress recovers to implemented P04. No destructive
rollback of this worktree is performed.

## Executable check

Run in MATLAB:

```matlab
run_checks
```

All assertions must pass before learner completion. Repository static checks and an independent Python
oracle do not substitute for execution in a licensed MATLAB runtime.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you allocate
Functions Across Hardware and Software?” State the allocation mechanism first and the system consequence second.
