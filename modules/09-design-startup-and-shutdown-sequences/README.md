# P09 — Design Startup and Shutdown Sequences

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 3:** Sequencing and synchronization  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you design Startup and Shutdown Sequences?

## Mental model: an ordered proof

A correct final snapshot is necessary but not sufficient. A lifecycle sequence is an ordered proof that every
action consumed the right facts before changing the system:

```text
step_ok(k) = evaluated(k) AND guard(k) AND postcondition(k)
lifecycle_ok = all(startup step_ok) AND running_snapshot
               AND all(shutdown step_ok) AND safe_off_snapshot
```

The deterministic teaching system is a logical controller, P08 interface, and actuator. Startup asserts a safe
command, energizes power, boots the controller, qualifies the P08 contract, enables the actuator, and only then
releases commands. Shutdown inhibits new commands, commands a safe output, disables the actuator, confirms
quiescence, closes the P08 interface, and only then removes power.

This is a source-level lifecycle model. Words such as safe, hazard, running, and quiescent name modeled Boolean
conditions; they do not establish physical equipment safety.

## P08 prerequisite contract

P08 separates record conformance from input eligibility. P09 consumes both facts:

- `p08ContractConformant` permits the interface-qualification action;
- `p08InputEligible` permits actuator enable and command release;
- eligibility cannot be true when conformance is false.

P09 does not invoke P08, add a field to its record, or claim that a producer, receiver, transport, or hardware
interface ran. It sequences already-observed facts.

## Deterministic baseline

The baseline startup places actuator enable at action 5, after power, controller boot, and P08 qualification.
Shutdown places power removal at action 6, after command inhibit, safe command, actuator disable, confirmed
quiescence, and interface close. Every precondition and postcondition passes, the intermediate running snapshot
is `[1 1 1 1 0 0 0]`, and the final safe-off snapshot is `[0 0 0 0 1 1 1]` in the documented state order.

The two complementary baseline views show:

1. each startup and shutdown guard beside its postcondition;
2. all seven logical state flags after each of twelve lifecycle actions.

Both views matter. The first explains why an action was allowed; the second shows the transient effect.

## Lever 1 — actuator-enable position

Move actuator enable from position 5 toward position 1 while leaving shutdown, P08 facts, faults, events, and
assessment fixed. The missing-prerequisite count is `[3 3 2 1 0]`. Every proposal still reaches the same final
running configuration, but only position 5 retains complete ordered evidence.

This lever makes a startup error visible: later actions can repair a final configuration without erasing the
fact that enable was requested before power, controller, or interface qualification.

## Lever 2 — power-removal position

Reset startup to position 5, then move shutdown power removal from position 1 through position 6. Missing
prerequisites decrease as `[5 4 3 2 1 0]`: command inhibit, safe command, actuator disabled, quiescence confirmed,
and interface closed. Every proposal finishes with the same off configuration; only position 6 proves the
shutdown ordering.

Action position is a dimensionless index, not elapsed time. P09 does not calculate duration, retry delay,
latency, jitter, deadline margin, or clock alignment.

## Cancellation, timeout, rollback, and recovery

Cancellation and timeout are injected logical events after the third proposed startup action. They contain no
timestamp or milliseconds. Either event masks the remaining startup actions, prevents shutdown evaluation, and
runs five bounded compensating actions to a modeled safe hold:

```text
inhibit commands → safe command → disable actuator
→ confirm quiescence and isolate controller/interface → remove power
```

Each compensating action has its own guard and observable result. With no injected shutdown fault, all five pass
and the terminal reports safe hold. A stuck actuator or missing quiescence can instead produce
`cancelled-rollback-incomplete` or `timed-out-rollback-incomplete`; `rollbackFailureMode` names the first failed
mechanism, so attempted compensation is never equated with successful compensation.

Because nominal shutdown is not evaluated, its state trace and final state remain unavailable (`NaN`). The
rollback trace is the only state record for compensation, including an incomplete safe-hold attempt.

If cancellation and timeout are asserted together, cancellation wins the reported tie. A fresh valid model call
after cancellation, timeout, incomplete rollback, a malformed input, or a fault reproduces the exact baseline
because the model has no persistent or global state.

## Deliberately broken final-state assessment

The broken `final-state-only` assessor looks only at the intermediate running snapshot and final safe-off
snapshot. With enable and power removal both at position 1, those snapshots eventually look correct, so the
broken assessor approves. The strict assessor evaluates the identical factual traces and rejects them because
transient guards failed. `falseApproval` exposes the lost evidence.

The assessor changes only reporting. It never rewrites action order, state traces, prerequisite truth,
postconditions, or the strict result.

## Failure modes and terminals

Inputs:

- startup enable position, 1–5 action index;
- shutdown power-removal position, 1–6 action index;
- P08 conformance and input-eligibility Booleans;
- injected actuator/quiescence fault, startup event, and assessment rule.

Observable effects:

- fixed action names and seven-state traces;
- evaluated, precondition, postcondition, step, and hazard flags;
- enable and power-removal prerequisite vectors and missing counts;
- intermediate running, final safe-off, rollback, strict/reporting, and false-approval results.

Handled terminals are `completed-safe-off`, `completed-with-hazard`, `cancelled-safe-hold`,
`timed-out-safe-hold`, `cancelled-rollback-incomplete`, and `timed-out-rollback-incomplete`. Named factual and
rollback failures distinguish invalid P08 facts, early enable, actuator-disable failure, missing quiescence,
early power removal, cancellation, and timeout. Malformed inputs are rejected before a trace is evaluated.

## Scope and future boundaries

- P10 will generalize states and transition rules; P09 owns one fixed lifecycle trace only.
- P11 will budget latency and jitter; P09 events have no elapsed-time semantics.
- P12 will address distributed synchronization; action indices and array order are not clock evidence.
- P13 will choose verification methods; P09 checks one deterministic source model.
- P18 will generalize fault containment; P09 retains only bounded compensating rollback.
- Static Python or source checks are not MATLAB runtime, UI, numerical-fidelity, protocol, bench, HIL, field,
  or production validation.

## Run

In MATLAB, from this folder:

```matlab
experiment
interactive
run_checks
```

Complete the interpretation prompts in `checks.md`, then give a two-sentence teach-back: ordered mechanism
first, modeled system consequence second.
