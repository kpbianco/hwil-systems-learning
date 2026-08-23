# Walkthrough: Trace a Command Path

1. Read the exact guiding question, then map the five command stages back to P04 functions and P05 owners.
2. Predict once whether a locally generated correction proves that the hardware-side input latch received it.
3. Run `experiment.m` and inspect only baseline stage reachability. Name the owner at each stage.
4. Inspect the degree-valued lineage, then the separate degree-per-update lineage. State why those units are not mixed.
5. In `interactive.m`, reset and lower only the authority limit below 30 deg. Observe the stop at validation.
6. Set the limit to exactly 30 deg and read the inclusive authority mechanism before moving another lever.
7. Reset, open only `B2`, then `B4`. For each, identify the last reached stage and first missing ownership handoff.
8. Read the boundary mechanism: a valid source output cannot prove that the next owner received it.
9. Inject cancellation, timeout, and their tie one at a time. Confirm no actuator input receipt and explain why no timing evidence was produced.
10. Open the final boundary and select the broken dispatch-only evidence. Compare local dispatch, endpoint receipt, and false success.
11. Restore endpoint-receipt evidence and the baseline controls to demonstrate stateless recovery.
12. Run `run_checks.m`, answer `checks.md` one prompt at a time, and teach back the tracing mechanism and consequence.
