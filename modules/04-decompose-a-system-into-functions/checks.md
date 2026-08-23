# Checks: Decompose a System into Functions

## Observation questions

Answer these interpretation questions one at a time after observing the corresponding view:

1. Which function first turns P03's desired behavior into an accepted or rejected system input?
2. Why does increasing response fraction change first tolerance entry as well as report time?
3. Why does increasing confirmation depth change report time but not first tolerance entry?
4. In the broken case, which function row is absent and which two error signals disagree?
5. Why is a local success report insufficient when the original request is not preserved end to end?
6. Which functions own rejection, cancellation, deadline miss, and trustworthy completion?
7. Why does this decomposition avoid deciding whether hardware or software performs each function?

## Independent and failure checks

`run_checks.m` derives the baseline from the geometric error law, checks both independent levers and
zero-response/unity-response/zero-request/signed/authority limits, and exercises rejection, timeout,
evidence depth beyond a deadline, exact deadline completion,
cancellation before motion, cancellation during motion, cancellation tied with completion or deadline, cancellation
after completion, the missing-validation false success, compatible numeric/text inputs, malformed inputs,
fixed resource bounds, recovery, and call isolation. It also checks the fixed function-contract and
activation dimensions and proves that no trace changes after a terminal result. The position-only rule is
an instructional confirmation proxy; P03 still owns the position-plus-velocity settling contract.
Post-terminal padding is deterministic trace termination; the model reports when safe hold is required but
does not claim that a physical hold command was issued or achieved.

Rollback is a source-and-manifest operation; the shared learner CLI suite covers recovery if a persisted
current module later becomes unavailable. No destructive rollback is performed by the MATLAB model.

## Executable check

Run in MATLAB:

```matlab
run_checks
```

All assertions must pass before learner completion. Repository static checks and an independent Python
oracle do not substitute for execution in a licensed MATLAB runtime.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you decompose a
System into Functions?” State the transformation mechanism first and the system consequence second.
