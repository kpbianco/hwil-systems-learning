# P10 lesson: Model System States and Transitions

## Guiding question

What inputs, observable effects, and failure modes matter when you model System States and Transitions?

## Compounds on P09

P09 treated startup and shutdown as one fixed ordered proof. P10 generalizes that idea into a finite-state
supervisor: each state change names its source, raw input, legal edge, guard, priority, requested destination,
and observed destination.
It consumes two composite P09 facts without running P09 or changing its interface:

```text
p09StartupProof = startupOrderValid AND startupFinalRunning
p09SafeOffProof = shutdownOrderValid AND shutdownFinalSafeOff
```

P10's event rollback is separate from P09's rollback trace and does not consume P09 `rollbackSafeHold`.

## Tutor opening

Ask one prediction before the baseline:

> If the trace ends in OFF, does that final state prove every intermediate transition was legal?

Show only the baseline state path first. Ask the learner to explain `OFF -> STANDBY`, `STANDBY -> READY`, and
`ACTIVE -> SAFE-HOLD` from the labels. Then show the guard/postcondition bars and ask what evidence the first
plot omitted. Do not start with MATLAB indexing or a state-enumeration API.

## Mechanism before MATLAB

Use this small transition contract:

```text
raw inputs -> priority -> requested destination
source + transition table + guard -> permission
observed destination -> postcondition
```

An evaluated step is strict only when its edge is legal, its guard is true, and the observed state matches the
strict destination. A state label alone compresses the history and cannot reconstruct those facts.

The six states are logical permissions for this lesson. `OFF`, `FAULT`, and `SAFE-HOLD` are not measurements
of voltage, stored energy, motion, or personnel safety.

## Baseline observation

With readiness and recovery depth both two, both P09 proofs true, nominal inputs, no event, and guarded fault
priority, the post-state IDs are:

```text
[2 2 3 3 3 4 4 4 4 4 4 6 1]
```

Ask why the second readiness observation moves STANDBY to READY and why stop goes to SAFE-HOLD rather than
directly to OFF. The intended explanation is evidence and guard ownership, not numeric state codes.

## Controlled transition 1 — readiness evidence depth

Reset the model. Move only `readinessConfirmations` through 1–4. READY appears at observation/event steps
`[2 3 4 5]`, while the number of observed STANDBY rows becomes `[1 2 3 4]`. Activation remains fixed at step 6.

Ask: “Which new fact caused this state-path delta?” The answer is the number of consecutive positive readiness
observations required by the STANDBY-to-READY guard. The count has no seconds or sample-period semantics.

## Controlled transition 2 — recovery evidence depth

Reset readiness depth to two, select `recoverable-feedback-loss`, and move only `recoveryConfirmations` through
1–4. Feedback loss selects FAULT at step 7. READY returns at steps `[8 9 10 11]`, while observed FAULT rows
become `[1 2 3 4]`.

Ask: “Why can recovery depth change without changing readiness depth?” They are independent guards on
different edges: STANDBY-to-READY and FAULT-to-READY.

## Negative cases: identify where the proof failed

Present one case at a time:

- Clear P09 startup proof. The first guard fails, state remains OFF, and later nominal rows are unavailable.
- Clear P09 safe-off proof. The final request is evaluated but state remains SAFE-HOLD.
- Select premature activation. ACTIVE is requested from STANDBY before readiness evidence, so the guard fails.
- Select state-stuck-active. The `ACTIVE -> FAULT` guard passes after feedback loss, but ACTIVE is observed, so
  the postcondition fails.

Correct the common statement “the transition failed” by asking whether the failed fact was the guard or the
observed destination. Those are different diagnoses.

## Cancellation, timeout, and rollback isolation

Inject cancellation, then timeout. Each preempts the scheduled activation at the fixed checkpoint after five
evaluated nominal rows. The scheduled raw activation input remains visible, but it is not evaluated; nominal
rows 6–13 and nominal final state stay unavailable. Read the separate three-row rollback trace:

```text
SAFE-HOLD -> SAFE-HOLD -> OFF
```

Clear P09 safe-off proof and repeat. The third rollback guard fails, so the observed state remains SAFE-HOLD
and rollback is incomplete. In a cancellation/timeout tie, cancellation has reporting precedence whether
rollback completes or not. These are asserted inputs without elapsed-time meaning.

Ask which outputs must remain unavailable. The answer is the preempted nominal trace and nominal final state,
not the separately evaluated rollback trace.

## Broken case — last request wins

Select `fault-reset-conflict` with guarded priority. At step 7 the raw input matrix contains feedback loss and
reset together. Strict priority selects FAULT. Recovery observations then permit READY.

Change only arbitration to `last-request-wins`. The raw matrix, source state, evidence counts, and strict
step-7 target remain identical. The broken arbiter selects reset, bypasses the legal-edge/recovery guard, and
observes READY with zero recovery confirmations. Its weak report later approves final OFF, while strict truth
rejects the actual trace.

Only the step-7 strict decision is the retained reference fact. Later targets follow the state actually
produced by the selected arbiter; the model does not fabricate an unexecuted counterfactual trace.

Then clear the P09 safe-off proof while leaving broken arbitration selected. The later OFF guard prevents a
final false approval, but it must not relabel the first step-7 priority bypass as a safe-off-only failure. Both
violations remain in the trace, and the first causal failure stays `fault-priority-bypassed`.

## Common misconceptions

- **“OFF proves the path was legal.”** No. A final label cannot recover discarded transition evidence.
- **“More confirmations means more milliseconds.”** No. The fixture contains ordered logical observations and
  no sample period.
- **“A true guard proves the transition happened.”** No. The state-stuck case separates permission from the
  observed postcondition.
- **“Reset should win because it was processed last.”** No. Textual order is not an engineering priority rule;
  fault priority must be explicit.
- **“Skipped means failed.”** No. Evaluated flags and `NaN` trace rows distinguish unavailable evidence from a
  false result.
- **“SAFE-HOLD proves hardware safety.”** No. Static source checks exercise no MATLAB UI, protocol peer, bench,
  HIL, or field system.
- **“Step order synchronizes equipment.”** No. P12 owns distributed synchronization.

## Inputs, observable effects, and failure modes

- Inputs: two bounded evidence depths, two P09 proof facts, scenario, asserted event, and arbitration policy.
- Observable effects: raw input rows, strict/reported target selection, table and guard truth, observed states,
  qualification steps, state-observation counts, rollback isolation, terminal, and false approval.
- Failure modes: missing prerequisite proof, illegal activation, failed state postcondition, fault-priority
  bypass, cancellation, timeout, incomplete rollback, and rejected malformed input.

## Interpretation and teach-back

Run `run_checks.m`, then use `checks.md` one prompt at a time. A satisfactory two-sentence teach-back names
the source/input/edge/guard/priority/postcondition mechanism first and explains one modeled consequence second.
MATLAB syntax is not part of the answer.
