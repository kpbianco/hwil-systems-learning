# P10 — Model System States and Transitions

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 3:** Sequencing and synchronization  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you model System States and Transitions?

## Mental model: state is a summary; transition evidence is the proof

A state label summarizes what the supervisor currently permits. It does not explain how the system arrived
there. Each evaluated transition therefore retains the relevant facts:

```text
source state + raw input(s) + legal edge + guard + priority
    -> requested destination -> observed destination

transition_ok(k) = table(source,target) AND guard(k)
                   AND observed(k) == target(k)
```

The bounded supervisor has six logical states: `OFF`, `STANDBY`, `READY`, `ACTIVE`, `FAULT`, and `SAFE-HOLD`.
Its 13-slot scenario moves from OFF through qualification and operation, then through SAFE-HOLD back to OFF.
These names are instructional logical conditions. They do not establish electrical state, stored-energy
release, actuator behavior, equipment safety, or personnel safety.

## P09 prerequisite adapters

P09 modeled one fixed startup/shutdown sequence. P10 consumes two composite proof facts without invoking P09:

```text
p09StartupProof = startupOrderValid AND startupFinalRunning
p09SafeOffProof = shutdownOrderValid AND shutdownFinalSafeOff
```

The first guards `OFF -> STANDBY`. The second guards `SAFE-HOLD -> OFF`, including event rollback. A snapshot
alone is deliberately insufficient. P10 does not change P09's arguments, outputs, traces, or ordering rules.

## Deterministic baseline

With two readiness confirmations, two recovery confirmations, both P09 proofs true, no injected event, the
nominal scenario produces this post-transition state-ID trace:

```text
[2 2 3 3 3 4 4 4 4 4 4 6 1]
```

That is `STANDBY, STANDBY, READY, READY, READY, ACTIVE` through step 11, then `SAFE-HOLD, OFF`. Every legal
edge, guard, and destination observation passes. The complementary views show the state path and the separate
guard/postcondition evidence; a final OFF label cannot replace either view.

## Lever 1 — readiness confirmation depth

Hold recovery depth at two and keep the P09 proofs, scenario, event, and arbitration fixed. Sweep required
readiness observations from 1 through 4. READY entry moves through steps `[2 3 4 5]`, and STANDBY observations grow
through `[1 2 3 4]` observations. Activation remains at step 6, so all four bounded proposals complete.

The lever changes evidence depth only. Observation/event step is dimensionless; it is not a sample period,
debounce duration, latency, jitter, or rate.

## Lever 2 — recovery confirmation depth

Reset readiness depth to two and inject one recoverable feedback loss at step 7. Sweep required recovery
observations from 1 through 4. FAULT exit moves through steps `[8 9 10 11]`, and FAULT observations grow through
`[1 2 3 4]` observations. All other facts remain fixed.

The mechanism is explicit: feedback loss has priority into FAULT, then consecutive recovery evidence permits
`FAULT -> READY`. A higher count does not prove more elapsed recovery time.

## Cancellation, timeout, rollback, and recovery

Cancellation and timeout are asserted logical inputs at the checkpoint before activation. Either one stops
nominal evaluation after step 5, leaves nominal steps 6–13 and the nominal final state unavailable, and starts
a separate three-transition rollback trace:

```text
enter SAFE-HOLD -> clear transition requests -> return to logical OFF with P09 safe-off proof
```

With the safe-off proof present, rollback reaches OFF. Without it, the final rollback guard fails and the
observed rollback state remains SAFE-HOLD; the terminal explicitly reports incomplete rollback. If cancellation
and timeout are asserted together, cancellation wins the reported tie. These events contain no timestamp,
deadline, or duration.

The model has no persistent or global state. A fresh valid call after a rejected guard, failed postcondition,
cancellation, timeout, incomplete rollback, malformed input, or broken arbitration reproduces the baseline.
P10 does not consume P09's `rollbackPerformed` or `rollbackSafeHold` outputs: its rollback trace is a distinct
lesson-local path, and its final OFF transition still requires the normal composite P09 safe-off proof.

## Deliberately broken conflict arbitration

The conflict scenario presents two raw inputs together at step 7: feedback loss and reset. The fixed raw-input
matrix is identical under both arbiters and never contains more than two simultaneous inputs.

The strict arbiter gives feedback loss priority, selects `ACTIVE -> FAULT`, and requires recovery evidence
before READY. The broken `last-request-wins` arbiter selects reset, attempts the illegal `ACTIVE -> READY` edge,
and observes READY with zero recovery confirmations. The selected edge and reset guard remain factually false;
an explicit weak-policy acceptance bit records that they were bypassed. Its weak report eventually approves
the final OFF state, while strict truth rejects the trace. Separate strict/reported targets, table results,
postconditions, priority violation, guard-bypass, and false-approval outputs preserve the strict step-7 reference decision. Later strict
targets are evaluated on whichever state the selected arbiter actually produced; P10 does not invent an
unexecuted counterfactual trace.

If the P09 safe-off proof is also absent, the final guard rejects the weak trace, so there is no final false
approval. The earlier step-7 priority bypass remains the first factual failure and is not masked by that later
rejection; both violations remain visible in the transition facts.

## Negative cases and terminals

- Missing P09 startup proof rejects the first transition and masks later nominal facts.
- Premature activation is rejected from STANDBY before any readiness evidence.
- `state-stuck-active` accepts the FAULT-transition guard but observes ACTIVE, so the postcondition fails.
- Missing P09 safe-off proof leaves nominal or rollback state in SAFE-HOLD.
- Cancellation and timeout preempt activation and isolate the nominal trace from rollback evidence.
- Malformed, non-scalar, non-finite, out-of-range, or unsupported inputs fail before a trace is returned.

Handled terminals are `completed-off`, `completed-false-approval`, `rejected-transition`,
`cancelled-rollback-complete`, `timed-out-rollback-complete`, `cancelled-rollback-incomplete`, and
`timed-out-rollback-incomplete`. The P09 composites are prevalidated lifecycle-design facts; P10's
`enter-standby-request` and `off-request` are supervisor inputs and do not command electrical power.

## Inputs, observable effects, and resource bounds

Inputs:

- readiness and recovery confirmation depths, each integer 1–4 observations;
- composite P09 startup and safe-off proof Booleans;
- one of five scenario modes, four event modes, and two arbitration modes.

Observable effects:

- fixed transition table, raw input matrix, source/strict target/reported target/observed state, and state trace;
- strict and reported guard, postcondition, transition, hazard, priority, and acceptance facts;
- readiness and recovery qualification steps, per-state observation counts, violations, terminals, and failures;
- a separate fixed three-row rollback trace when an event is observed.

Every result stays inside six states, 13 nominal observation/event attempt slots, three rollback slots, nine raw-input columns, four
readiness observations, four recovery observations, and at most two simultaneous scenario inputs. The model
uses base MATLAB operations, fixed deterministic data, and no solver, random source, external I/O, or device.

## Scope and future boundaries

- P11 owns elapsed latency and jitter; P10 observation/event indices have no time unit.
- P12 owns distributed clocks and synchronization; array order is not clock evidence.
- P13 owns verification-method selection; P10 retains only deterministic source checks.
- P18 owns generalized fault containment; P10 demonstrates one bounded event rollback.
- P20 owns configuration and calibration state; P10 states do not version parameters.
- Static Python/source checks are not MATLAB runtime, UI, numerical-fidelity, protocol, bench, HIL, field, or
  production validation.

## Run

In MATLAB, from this folder:

```matlab
experiment
interactive
run_checks
```

Complete `checks.md`, then give a two-sentence teach-back: transition mechanism first, modeled consequence
second.
