# Checks: Write a CONOPS from an Operator Goal

## Independent numerical checks

Run:

```matlab
run_checks
```

The checks independently recompute the baseline event sums, exercise zero and exact-deadline limits,
verify isolated command and feedback effects, and cover missing feedback, timeout, cancellation
priority, malformed inputs, bounded resources, repeatability, operational recovery after readiness
and feedback are restored, and numeric input compatibility.

## Interpretation questions

1. Why does increasing command latency move both the physical effect and confirmation?
2. Why can increasing feedback latency leave the physical-effect time unchanged but still fail the goal?
3. In the broken case, which exact assumption is violated, and what symptom distinguishes physical
   completion from operator-confirmed success?
4. Why must cancellation and timeout name a safe terminal state rather than only report an error?
5. Which P01 timing-budget quantities become CONOPS inputs here, and who needs to observe them?

## Limiting-case check

Explain the expected outcome when all three path/action times are zero and confirmation occurs at
the request time. Then explain the exact-deadline tie: confirmation is accepted at the deadline,
while cancellation at that same timestamp takes safety priority.

## Teach-back

In two sentences, turn the operator goal into a CONOPS. Include the trigger and physical effect in
the first sentence; include observable confirmation, deadline, safe failure response, and recovery
entry condition in the second. MATLAB syntax is not an acceptable substitute for the operational story.
