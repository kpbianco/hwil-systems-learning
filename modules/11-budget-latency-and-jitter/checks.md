# P11 checks: Budget Latency and Jitter

Use one prompt at a time after observing the corresponding view.

## Baseline interpretation

Explain why the nominal total is 3.3 ms, the bounded maximum is 4.0 ms, and the 4.2 ms deadline leaves only
0.2 ms. Then identify what the cycle-latency plot cannot show about stage ownership.

## Lever 1 — nominal transport latency

Why does adding 0.6 ms of transport latency subtract exactly 0.6 ms of deadline margin while leaving the
1.4 ms peak-to-peak jitter allocation unchanged?

## Lever 2 — jitter allocation

At fixed nominal transport latency, explain why raising jitter scale separates earliest and latest completion
without moving the nominal 3.3 ms total. State the zero-jitter limiting case.

## Deadline and event ordering

Explain why completion exactly at a deadline is on time, why cancellation at 15 ms leaves cycle 3 unfinished,
why cancellation exactly at a planned completion leaves that tied cycle unfinished, and why cancellation wins
when it coincides with the 22.2 ms timeout.

## Rollback and recovery boundary

What does P11 know after requesting P10 SAFE-HOLD? Distinguish a handoff request, rollback required, rollback
evidence unavailable, and a fresh stateless model call that reproduces the baseline.

## Broken-case diagnosis

Name the exact assumption violated by `rss-uncorrelated`. Explain how all four stages can remain inside their
allocations while the aligned 4.7 ms cycle contradicts the reported 4.075 ms approval.

## Curriculum transfer

Contrast P11's finite deterministic bound with P01's seeded Gaussian/P99 sampler and with P12's future
distributed-clock synchronization problem. Do not describe the P11 fixture as probability or synchronization
evidence.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you budget Latency
and Jitter?” Name the additive timing mechanism first and one deadline, cancellation, timeout, or reporting
consequence second. Do not rely on MATLAB syntax.

## Executable check

Run:

```matlab
run_checks
```

All assertions must pass before personal completion is recorded. Source inspection alone is not MATLAB-runtime,
UI, numerical-fidelity, bench, HIL, or field validation.
