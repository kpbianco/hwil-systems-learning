# P09 walkthrough: Design Startup and Shutdown Sequences

1. Read the exact guiding question and connect P08 conformance/input eligibility to P09 startup prerequisites.
2. Predict once whether correct final running and off snapshots prove safe transient ordering.
3. Run `experiment.m`; inspect only the baseline startup guard/postcondition view and explain enable position 5.
4. Inspect only the baseline shutdown view and distinguish actuator disabled from quiescence confirmed.
5. View the seven-state lifecycle trace and identify the intermediate running and final safe-off snapshots.
6. In `interactive.m`, reset and move actuator enable through positions 1–5. Name the missing fact at each change.
7. Read the startup mechanism, reset, and leave every other control fixed.
8. Move shutdown power removal through positions 1–6. Explain why position 6 is the limiting valid case.
9. Inject nonconformant and ineligible P08 facts separately; do not call either case protocol or hardware execution.
10. Inject actuator-stuck and quiescence-not-confirmed faults one at a time and inspect postcondition failures.
11. Inject cancellation, timeout, and their tie. Confirm successful guarded rollback and unavailable nominal shutdown trace/final state.
12. Combine early enable, actuator-stuck-on, and cancellation; then combine missing quiescence with timeout and the cancellation/timeout tie. Diagnose incomplete rollback while preserving cancellation tie precedence.
13. Restore baseline to demonstrate stateless recovery.
14. Put both positions at 1, compare strict assessment with broken final-state-only assessment, and diagnose false approval.
15. Run `run_checks.m`, answer `checks.md` one prompt at a time, and give the mechanism-first teach-back.
