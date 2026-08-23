# Lesson: Decompose a System into Functions

## Guiding question

What inputs, observable effects, and failure modes matter when you decompose a System into Functions?

## From P03 behavior to a function chain

P03 defined the requested rotary angle, valid authority, observed position, tolerance, and response deadline.
P04 keeps those quantities and asks a new question: which transformations must exist for the system—not
just one local element—to produce and truthfully report that behavior?

A verb-noun decomposition for this transaction is:

1. capture intent;
2. validate authority;
3. observe position;
4. compute signed error;
5. generate a bounded correction;
6. update physical state;
7. confirm requested behavior;
8. handle cancellation;
9. enforce the deadline;
10. report the outcome.

For each function, `model.m` retains a consuming input, a produced output, a failure mode, and an activation
trace. This says what must happen without saying whether a processor, FPGA, sensor, actuator, or operator
performs it. That allocation belongs to P05; detailed command and measurement paths belong to P06 and P07.

## Transparent transformation and evidence rule

At each 20-millisecond functional update, the motion-producing chain applies

```text
error[k]      = effective_target - observed_position[k]
correction[k] = response_fraction * error[k]
position[k+1] = position[k] + correction[k]
```

For `0 <= response_fraction <= 1`, the remaining local error follows

```text
local_error[k] = local_error[0] * (1 - response_fraction)^k
```

The completion function is deliberately distinct from motion generation. It requires the original request
error to be within tolerance for `N` consecutive observations. This is a visible evidence-persistence proxy,
not a replacement for P03's position-plus-velocity sustained-settling proof and not evidence that the state
will remain in band forever. Increasing the response fraction changes when the proxy first enters tolerance.
Increasing `N` leaves that entry unchanged and delays the report by exactly `(N - 1) * 20 ms` for this
monotonic trace. The fixed interval is an instructional function-update tick, not a P06 command-path or P11
timing-budget model.

## Inputs, observable effects, and terminal paths

- Requested angle and cancellation are external transaction inputs inherited from P02.
- Authority, response fraction, tolerance, confirmation depth, and deadline are declared functional inputs.
- Position, request error, local monitor error, correction, function activation, and terminal report are
  observable effects.
- Rejection prevents an invalid request from reaching motion functions.
- At cycle zero, valid intent is captured and validated before any correction; an invalid request is rejected
  without motion, while confirmation depth one may accept a zero request immediately.
- Cancellation and deadline are supervisory guards, not serial motion stages. Cancellation stops an active
  transaction trace before further modeled side effects, emits a safe-hold requirement, and wins an exact
  tie with completion or the deadline.
- Confirmation at the inclusive deadline passes; deadline enforcement otherwise reports a miss at the named
  update and emits a safe-hold requirement without allowing late motion to count as success.
- A fresh call starts from zero again, so rejection, cancellation, timeout, and broken cases cannot leak state.

After any terminal report, the fixed-size output repeats the last modeled position and emits zero further
correction. That is trace termination for deterministic comparison—not a commanded or verified physical hold.

## Deliberately broken preservation of intent

The broken architecture removes `Validate authority` and changes the confirmation input from the original
request to the locally clipped target. A 70-degree request with only 45 degrees of authority then moves toward
45 degrees and can report local completion. The system still has about 25 degrees of request error, so the
reported success is false. The symptom is not merely clipping; it is a missing function plus an end-to-end
input replaced at a downstream boundary.

## Common mistakes

- Naming components instead of verb-noun transformations allocates a solution before the needed behavior is clear.
- A block diagram is incomplete when a function has no declared input, output, failure, or observable evidence.
- Local target error is not interchangeable with original request error.
- Confirmation depth changes evidence time, not the motion law or first tolerance entry.
- Cancellation and timeout need explicit owners; treating them as exceptional afterthoughts leaves no safe terminal path.
- Position-only evidence persistence is not the same as P03's physical settling proof.
- More functions are not automatically better—the smallest complete set preserves intent and covers every terminal outcome.

## Completion standard

Explain how the correction and confirmation levers affect different observables, diagnose the omitted-validation
case from local versus request error, pass `run_checks.m`, and give a two-sentence teach-back: transformation
mechanism first, system consequence second.
