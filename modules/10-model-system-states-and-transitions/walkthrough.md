# P10 walkthrough: Model System States and Transitions

1. Read the exact guiding question and connect P09's fixed ordered proof to P10's reusable transition contract.
2. Predict once whether a final OFF label proves that every intermediate transition was legal.
3. Run `experiment.m`; inspect only the baseline state path and explain OFF → STANDBY → READY.
4. Inspect only the complementary edge/guard/postcondition view and name the evidence hidden by a state label.
5. In `interactive.m`, reset and move readiness confirmations through 1–4. Observe READY steps `[2 3 4 5]`.
6. Read the readiness mechanism, reset, and leave the recovery, P09, scenario, event, and arbitration inputs fixed.
7. Select recoverable feedback loss and move recovery confirmations through 1–4. Observe FAULT exit steps `[8 9 10 11]`.
8. Clear P09 startup proof and safe-off proof separately; distinguish a rejected first guard from a rejected final guard.
9. Select premature activation, then state-stuck-active. Distinguish an illegal source/guard from a passed guard with a failed destination observation.
10. Inject cancellation and timeout separately. Confirm that the scheduled activation and all later nominal rows are unavailable while rollback has its own trace.
11. Inject their tie and explain cancellation precedence without assigning an elapsed-time unit.
12. Clear P09 safe-off proof with cancellation and with the tie. Confirm SAFE-HOLD remains observed and rollback is explicitly incomplete.
13. Restore baseline to demonstrate stateless recovery after rejection, event handling, and incomplete rollback.
14. Select fault/reset conflict under guarded priority, then change only arbitration to broken last-request-wins. Verify identical raw inputs but different selected targets, guard bypass, priority violation, and false approval.
15. Leave broken arbitration selected and clear P09 safe-off proof. Verify the later rejection removes false approval without masking the first step-7 priority-bypass diagnosis.
16. Run `run_checks.m`, answer `checks.md` one prompt at a time, and give the two-sentence mechanism-first teach-back.

Observation/event step is dimensionless. The logical states and requests are not MATLAB-runtime, electrical,
bench, HIL, field, or personnel-safety evidence.
