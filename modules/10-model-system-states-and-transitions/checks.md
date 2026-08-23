# P10 checks: Model System States and Transitions

Run `run_checks.m` before answering these prompts. Static Python/source checks are not MATLAB execution.

## Numerical and limiting checks

1. In state order `OFF, STANDBY, READY, ACTIVE, FAULT, SAFE-HOLD`, why is the baseline trace `[2 2 3 3 3 4 4 4 4 4 4 6 1]`?
2. Why do readiness depths 1–4 produce READY steps `[2 3 4 5]` and STANDBY observation counts `[1 2 3 4]`?
3. Why do recovery depths 1–4 produce FAULT exit steps `[8 9 10 11]` and FAULT observation counts `[1 2 3 4]`?
4. Which values are the inclusive minimum and maximum of each lever, and why must zero, five, fractional, non-finite, complex, vector, or text values be rejected?
5. Verify that six states, 13 nominal attempt slots, three rollback slots, nine raw-input columns, four readiness observations, four recovery observations, and at most two simultaneous scenario inputs bound every result.

## Guard, event, rollback, and recovery checks

1. Why does P10 use `startupOrderValid && startupFinalRunning` rather than P09 `startupOrderValid` alone?
2. Why does P10 use `shutdownOrderValid && shutdownFinalSafeOff` rather than the final safe-off snapshot alone?
3. How does premature activation differ from state-stuck-active: which one fails edge/guard evidence, and which one fails the observed destination?
4. After cancellation or timeout, which nominal rows and final-state facts are unavailable, and which three rollback rows are separately evaluated?
5. Why must rollback pass require legal edge, guard, and postcondition for every row?
6. What distinguishes complete rollback ending in OFF from incomplete rollback retained in SAFE-HOLD?
7. In the cancellation/timeout tie, which terminal is selected for complete and incomplete rollback, and why does that priority carry no elapsed-time meaning?
8. How does an exact baseline call after each malformed, rejected, cancelled, timed-out, incomplete, stuck, or broken call demonstrate stateless recovery and call isolation?

## Broken arbitration and interpretation

1. At the fault/reset conflict, which two raw-input bits are true and why must they remain identical under both arbitration modes?
2. What strict step-7 target does fault priority select? What target does last-request-wins select?
3. In the broken run, why are the selected reset edge and reset guard factually false even though the weak policy accepts the step and observes READY?
4. Why are `guardBypassed`, `priorityViolation`, factual transition pass, weak policy acceptance, strict acceptance, and false approval separate outputs?
5. Why does a final OFF label prove neither correct arbitration nor a legal intermediate path?
6. If missing P09 safe-off proof later rejects the broken trace, why must the first factual failure remain the step-7 priority bypass while both violations stay visible?
7. Why are observation/event steps and observation counts not latency, sample period, jitter, synchronization, or recovery-time evidence?
8. Which claims still require licensed MATLAB runtime, UI review, protocol, bench, HIL, or field evidence?

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you model System States and Transitions?”

- Sentence 1: explain source state, raw input, legal edge, guard, priority, and observed-destination mechanism.
- Sentence 2: explain one modeled consequence of missing P09 proof, premature activation, failed postcondition,
  cancellation/timeout rollback, or last-request-wins false approval.
