# P09 checks: Design Startup and Shutdown Sequences

Run `run_checks.m` before answering these prompts. Passing static source tests alone is not MATLAB execution.

## Numerical and limiting checks

1. Why do startup enable positions 1–5 have missing-prerequisite counts `[3 3 2 1 0]`?
2. Why do shutdown power-removal positions 1–6 have counts `[5 4 3 2 1 0]`?
3. Which position is the inclusive valid boundary for each lever, and which adjacent position is rejected?
4. Verify that the baseline running snapshot is `[1 1 1 1 0 0 0]` and safe-off is `[0 0 0 0 1 1 1]` in the documented state order.
5. Why must `p08InputEligible=true` with `p08ContractConformant=false` be rejected as inconsistent input?

## Failure, event, and recovery checks

1. How does an actuator-disable postcondition failure differ from missing quiescence confirmation?
2. After cancellation or timeout, which startup rows are evaluated, why are the nominal shutdown trace and final state unavailable, and which five rollback actions execute?
3. Why must rollback safe hold require every rollback guard and postcondition, rather than only an attempted rollback or final power-off bit?
4. What distinguishes `cancelled-rollback-incomplete` after a stuck actuator from `timed-out-rollback-incomplete` after missing quiescence?
5. In the cancellation/timeout tie, which terminal is reported when rollback succeeds and when it is incomplete, and why does that precedence have no elapsed-time meaning?
6. How does a valid call after each malformed, cancelled, timed-out, faulted, or broken-assessment call prove stateless recovery?
7. Why are unevaluated guards false while their state-trace rows are `NaN`?

## Interpretation questions

1. A proposal reaches running and later reaches safe-off. What transient evidence is still required before strict approval?
2. Why is a P08-conformant record with ineligible input insufficient for actuator enable?
3. Why does action index not establish latency, jitter, or distributed synchronization?
4. What makes the final-state-only case a reporting failure instead of a different factual trace?
5. Which parts of this model would require MATLAB runtime, UI review, protocol, bench, or HIL evidence before making stronger claims?

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you design Startup and Shutdown Sequences?”

- Sentence 1: explain the ordered guard/action/postcondition mechanism.
- Sentence 2: explain one modeled consequence of early enable, early power removal, guarded rollback, or final-state-only false approval.
