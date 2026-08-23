# P11 — Budget Latency and Jitter

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 3:** Sequencing and synchronization  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you budget Latency and Jitter?

## Mental model: a deadline needs both nominal delay and bounded variation

P10 established whether an activation transition was logically justified. P11 begins only after consuming a
caller-supplied composite fact:

```text
p10ActivationStep = 6  (P10's nominal activate-request)
p10ActivationProof = transitionTableAllowed(p10ActivationStep)
                     AND strictGuardPass(p10ActivationStep)
                     AND strictPostconditionPass(p10ActivationStep)
                     AND NOT priorityViolation(p10ActivationStep)
```

P11 then assigns elapsed time to four owned stages of a repeated command cycle. For cycle `k` and stage `i`:

```text
d(k,i) = n(i) + s J(i) P(k,i)
L(k)   = sum_i d(k,i)
L_wc   = sum_i n(i) + s sum_i J(i)
margin = deadline - L_wc
```

`n(i)` is nominal latency in milliseconds, `J(i)` is the stage jitter allocation in milliseconds, `s` is a
dimensionless scale, and the fixed pattern `P(k,i)` is `-1`, `0`, or `1`. The bounded sum makes no cancellation
or independence assumption. Deadline equality is on time; a timeout occurs only when completion is later than
the absolute deadline.

## Deterministic fixture and baseline

The model contains 12 scheduled cycles on one ideal time base, separated by 6 ms. It uses four stages:

| Stage | Nominal latency | Baseline jitter allocation |
| --- | ---: | ---: |
| Input acquisition | 0.6 ms | ±0.1 ms |
| Command calculation | 0.5 ms | ±0.1 ms |
| Command transport | 1.2 ms | ±0.3 ms |
| Apply and observe | 1.0 ms | ±0.2 ms |

At the 4.2 ms deadline, the baseline nominal latency is 3.3 ms, the additive upper bound is 4.0 ms, and the
worst-case margin is 0.2 ms. The fixed pattern is balanced by stage and includes aligned positive and negative
rows, so the 12 planned latencies have a 3.3 ms mean and 1.4 ms peak-to-peak jitter. This finite fixture is not
a probability distribution, percentile, measured clock, or runtime trace.

The first baseline view shows planned versus completed-cycle latency and the deadline. The complementary view
shows cumulative nominal, earliest, and latest elapsed time across the four owners. Planned values remain an
offline design artifact after an interruption; actual fields become unavailable (`NaN`) for every unfinished
or unstarted cycle.

## Lever 1 — nominal command-transport latency

Hold jitter scale at one, deadline at 4.2 ms, P10 proof true, cancellation disabled, and bounded-sum assessment
selected. Sweep transport latency through `[0.6 1.2 1.8 2.4]` ms. The strict upper bounds become
`[3.4 4.0 4.6 5.2]` ms and margins become `[0.8 0.2 -0.4 -1.0]` ms.

The mechanism is one-for-one addition: one extra transport millisecond adds one end-to-end millisecond. It
does not widen the jitter envelope, whose peak-to-peak allocation remains 1.4 ms.

## Lever 2 — bounded jitter scale

Reset transport latency to 1.2 ms and sweep jitter scale through `[0 0.5 1 1.5 2]`. The strict upper bounds
become `[3.3 3.65 4.0 4.35 4.7]` ms, margins become `[0.9 0.55 0.2 -0.15 -0.5]` ms, and peak-to-peak
jitter becomes `[0 0.7 1.4 2.1 2.8]` ms.

This lever leaves nominal latency fixed. It widens earliest and latest completion symmetrically because every
owned allocation is multiplied by the same dimensionless stress factor.

## Cancellation, timeout, rollback authority, and recovery

Cancellation is an absolute scenario time. It wins a tie with release, completion, or deadline. At 15 ms,
cycles 1 and 2 complete, cycle 3 has started, and cycle 3 onward has no completed latency evidence.

Timeout is derived rather than asserted. At jitter scale two, cycle 4 is released at 18 ms, its deadline is
22.2 ms, and its planned 4.7 ms completion would arrive at 22.7 ms. The timeout therefore occurs at 22.2 ms,
before completion. A cancellation at exactly 22.2 ms records both causes and reports cancellation precedence.

Either observed interruption requests a P10 `SAFE-HOLD` handoff. P11 records that rollback is required while
keeping `rollbackEvidenceAvailable = false` and `rollbackAuthority = 'P10'`. A request is not evidence that the
state transition, electrical action, or rollback occurred. The model has no persistent or global state, so a
fresh baseline call after cancellation, timeout, malformed input, blocked proof, or broken assessment recovers
exactly.

## Deliberately broken assessment — unproven RSS cancellation

The `rss-uncorrelated` option reports

```text
L_rss = sum_i n(i) + sqrt(sum_i (s J(i))^2)
```

At jitter scale two it reports about 4.075 ms and approves the 4.2 ms deadline. The governing bounded sum is
4.7 ms, and the fixed aligned cycle reaches 4.7 ms while every stage remains inside its allocation. The actual
timeout and explicit `falseApproval` expose the violated assumption: no evidence established independent,
zero-cancelling stage variation. RSS is shown only as the deliberately broken case, not as an accepted timing
contract.

## Inputs, observables, failures, and bounds

Inputs:

- command-transport nominal latency, 0.6–2.4 ms;
- jitter-allocation scale, 0–2 dimensionless;
- end-to-end deadline, 0.5–10 ms;
- one Boolean P10 activation-proof adapter;
- nonnegative cancellation time in ms or `Inf` for none;
- bounded-sum or deliberately broken RSS assessment.

Observables include per-stage planned latency, cumulative stage completion, release/deadline/completion time,
planned and completed-cycle latency, nominal and bounded totals, strict and reported margin, peak-to-peak
jitter, start/completion masks, interruption time, handoff request, acceptance, and false approval.

Failure modes are malformed or out-of-range input, missing P10 proof, cancellation, derived timeout,
cancellation/timeout tie, unavailable post-terminal evidence, and RSS false approval. The resource envelope is
fixed at 12 cycles, four stages, and 48 stage cells. The model uses base MATLAB arithmetic and fixed data with
no RNG, solver, timer, file/network/device I/O, Simulink, global state, or persistent state.

## Curriculum and evidence boundaries

- P01 introduces a seeded Gaussian/P99 closed-loop sampler. P11 instead owns a finite deterministic schedule,
  allocated bounds, event ordering, and design-assessment truth; it makes no probability claim.
- P10 owns state legality, guards, priority, observed destinations, SAFE-HOLD, and rollback. P11 consumes one
  activation-proof fact and can request a handoff but cannot prove those actions.
- P12 owns distributed clocks, timestamp offset, drift, skew, and synchronization. P11 uses one ideal time base;
  its array order is not synchronization evidence.
- Source inspection and the independent Python oracle are not MATLAB-runtime, UI, numerical-fidelity, bench,
  HIL, field, or production validation.

## Run

In MATLAB, from this folder:

```matlab
experiment
interactive
run_checks
```

Complete `checks.md`, then give a two-sentence teach-back: additive timing mechanism first, modeled consequence
second.
