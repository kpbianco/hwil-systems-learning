# Checks: Trace a Measurement Data Path

## Observation and interpretation questions

Answer one question after the corresponding view:

1. How do P05's hardware observation and P06's scalar `observedAngleDeg` input bound this path?
2. Why is model truth a comparison reference rather than a sixth measurement-path signal?
3. Which owner emits volts, counts, calibrated degrees, and the validity-qualified payload?
4. Why must the plots keep volts, counts, degrees, milliseconds, and Booleans separate?
5. What does increasing ADC bits change, and what does the half-LSB bound not cover?
6. At sample age exactly equal to the freshness limit, why is the sample valid?
7. How can value and reachability remain unchanged while usability changes?
8. How does an empty reached prefix differ from received data carrying an invalid quality flag?
9. What does cancellation win in the injected cancellation/timeout tie, and what timing fact remains unknown?
10. Which evidence does the broken value-only assessment ignore?
11. Why does receipt at P07's qualified-control intake prove neither P06 consumption, physical sensing, nor control response?
12. Why does `p06InputEligible` gate a scalar rather than add a validity argument to P06?

## Independent, negative, and recovery checks

`run_checks.m` independently reconstructs the sensor, ADC, calibration, and freshness equations and verifies
stage/owner/unit identity, the fixed five-stage/four-boundary envelope, baseline voltage/count/value, half-LSB
error, ADC minimum/maximum resolution, positive/negative/zero/full-scale angles, inclusive sensor and freshness
limits, just-outside saturation and staleness, every open boundary, cancellation, timeout, tie precedence,
entry-event isolation, valid/invalid/missing states, complete versus value-only reporting, compatible scalar
inputs, P06 scalar-adapter eligibility, upper and lower saturation, malformed numeric and categorical inputs,
fixed resource bounds, call isolation, and exact recovery. P06 accepts only the scalar `observedAngleDeg`; P07
does not add a validity input to P06.

Timeout and cancellation are already-asserted logical guards; the checks do not measure elapsed path time,
scheduling, retries, jitter, or achieved safety. Repository Python tests execute an independently written
formula and path oracle plus static source checks; they do not execute MATLAB.

Rollback is a source-and-manifest operation. The durable Python fixture rolls P07 and every later module back
inside an isolated copy, then proves persisted P07 progress recovers to implemented P06. It never changes the
real learner state or worktree during validation.

## Executable check

Run in MATLAB:

```matlab
run_checks
```

All assertions must pass before learner completion. Static checks cannot substitute for execution in a named
licensed MATLAB runtime.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you trace a
Measurement Data Path?” State the value-plus-quality mechanism first and the system consequence second.
