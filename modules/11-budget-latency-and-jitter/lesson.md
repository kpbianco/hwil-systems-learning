# P11 lesson: Budget Latency and Jitter

## Guiding question

What inputs, observable effects, and failure modes matter when you budget Latency and Jitter?

## Compounds on P10 without replacing P01 or P12

P10 made every logical transition explainable through its source, legal edge, guard, priority, and observed
destination. It deliberately assigned no time unit to its observation/event index. P11 consumes one composite
activation-proof fact from P10's nominal `activate-request` transition at step 6 and asks a new question: after
logical permission exists, can a repeated timed command cycle finish before its elapsed deadline?

P01 introduced a seeded Gaussian/P99 timing sampler. This lesson goes deeper into deterministic allocation,
event ordering, and false design approval; it does not reinterpret a finite fixture as probability. P12 will
own multiple clocks and synchronization. P11 uses one ideal time base, so no clock offset, skew, drift, or
timestamp-alignment claim follows from these arrays.

## Tutor opening

Ask one prediction before showing the baseline:

> If each stage remains inside its own jitter allocation, can an RSS total still approve a deadline that one
> aligned cycle misses?

Show only the scheduled-cycle latency trace first. Ask the learner to locate the 4.2 ms deadline and identify
the slowest completed cycle. Then show the cumulative stage envelope and ask what ownership evidence the first
plot omitted. Do not start with MATLAB array construction or UI callbacks.

## Mechanism before MATLAB

For stage `i` in cycle `k`:

```text
stage latency       d(k,i) = nominal(i) + scale * allocation(i) * pattern(k,i)
end-to-end latency  L(k)   = sum_i d(k,i)
bounded maximum     L_wc   = sum_i nominal(i) + scale * sum_i allocation(i)
deadline margin     M      = deadline - L_wc
```

All latency, deadline, and margin quantities use milliseconds. Scale and scheduled-cycle index are
dimensionless. `M >= 0` passes the bounded design budget; equality is on time. The additive jitter allowance
does not assume that stages cancel one another.

## Baseline observation

The four nominal stage latencies are `[0.6 0.5 1.2 1.0]` ms and the baseline allocations are
`[0.1 0.1 0.3 0.2]` ms. The nominal total is 3.3 ms, the bounded maximum is 4.0 ms, and the 4.2 ms deadline
leaves 0.2 ms. The fixed 12-cycle trace is:

```text
[3.3 3.5 3.6 4.0 3.1 3.3 3.1 2.6 3.2 3.4 3.2 3.3] ms
```

The aligned maximum and minimum make observed peak-to-peak jitter 1.4 ms. Each pattern column sums to zero,
so the finite trace mean equals the nominal total. That balance is a fixture fact, not statistical evidence.

## Controlled transition 1 — nominal transport latency

Reset the model. Move only transport nominal latency through `[0.6 1.2 1.8 2.4]` ms. The bounded maximum
moves through `[3.4 4.0 4.6 5.2]` ms and the margin through `[0.8 0.2 -0.4 -1.0]` ms. Ask:

> Which new term caused this view to move, and why did peak-to-peak jitter stay fixed?

The answer is a nominal stage delay. It shifts every end-to-end latency one-for-one but does not change the
allocated variation around nominal.

## Controlled transition 2 — jitter scale

Reset transport to 1.2 ms. Move only jitter scale through `[0 0.5 1 1.5 2]`. Nominal latency remains 3.3 ms,
while the bounded maximum grows through `[3.3 3.65 4.0 4.35 4.7]` ms and peak-to-peak jitter through
`[0 0.7 1.4 2.1 2.8]` ms. Ask:

> Why can the latest completion move while the nominal line does not?

The allocation scale multiplies deviations, not nominal work. It widens the envelope symmetrically.

## Missing proof and unavailable execution evidence

Clear the P10 activation proof. The offline plan and bounds remain calculable, but no cycle starts and all
actual latency/completion fields remain unavailable. Correct the statement “the timing failed”: timing was not
executed because logical authorization was unavailable.

## Cancellation, timeout, and rollback boundary

At cancellation time 15 ms, two cycles have completed and cycle 3 has started. Cancellation precedes its
planned 15.6 ms completion, so actual latency for cycle 3 and every later cycle is unavailable. The offline plan
remains visible to distinguish design intent from observed evidence.

At jitter scale two, cycle 4 releases at 18 ms. Its absolute deadline is 22.2 ms and planned completion is
22.7 ms, so timeout is derived at 22.2 ms. A cancellation at exactly 22.2 ms records both causes and resolves
to cancellation. Deadline equality without cancellation is on time.

Both events request a P10 SAFE-HOLD handoff. P11 records rollback required, evidence unavailable, and P10 as
the authority. Never turn the request into a claim that SAFE-HOLD, electrical action, or rollback occurred.

## Broken case — root-sum-square without independence evidence

Keep the same stage data and fixed pattern at jitter scale two. The broken RSS report uses about 4.075 ms and
approves the 4.2 ms deadline. Strict addition gives 4.7 ms, and cycle 4 aligns all positive stage allocations
to reach it. Every stage remains locally inside bounds, yet the end-to-end deadline expires.

The violated assumption is not “jitter exists.” The error is treating independent, canceling stage variation
as proven when the contract supplied only bounded allocations. Preserve the identical factual trace under both
assessments; change only the reporting rule.

## Common misconceptions

- **“Mean 3.3 ms proves the deadline.”** No. The deadline is compared with bounded latest completion.
- **“Jitter is the same as latency.”** No. Latency is elapsed completion time; jitter is variation around a
  reference. Peak-to-peak jitter is a width, not a one-sided allowance.
- **“RSS is always conservative.”** No. It is smaller than an additive bound and needs a justified dependence
  model before it can replace that bound.
- **“A timeout measures late completion.”** Here the timed-out completion is unavailable; timeout occurs at
  the deadline before the planned completion.
- **“Cancellation erases the plan.”** No. It masks unfinished actual evidence, while offline planned values
  stay inspectable.
- **“SAFE-HOLD requested means rollback succeeded.”** No. P10 owns the state transition and rollback proof.
- **“One ordered array proves synchronization.”** No. P12 owns distributed-clock evidence.
- **“The fixed trace is a percentile.”** No. No randomness, population, or probability model is present.

## Inputs, observable effects, and failure modes

- Inputs: transport nominal delay, bounded jitter scale, elapsed deadline, P10 activation proof, absolute
  cancellation time, and assessment rule.
- Observable effects: stage allocations, cumulative envelope, cycle releases/deadlines/completions, planned and
  completed latency, strict/reported margin, completion masks, event time, handoff request, and false approval.
- Failure modes: malformed input, missing authorization, cancellation, derived timeout, tie precedence,
  unavailable post-terminal evidence, and unproven-RSS false approval.

## Interpretation and teach-back

Run `run_checks.m`, then use `checks.md` one prompt at a time. A satisfactory two-sentence teach-back names
the additive nominal-plus-bounded-jitter mechanism first and explains one deadline, cancellation, timeout, or
false-approval consequence second. MATLAB syntax is not part of the answer.
