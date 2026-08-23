# Walkthrough: Trace a Measurement Data Path

1. Read the exact guiding question, then connect P05's hardware-owned `Observe position` to eligibility for P06's unchanged scalar `observedAngleDeg` input.
2. Predict once whether a finite stale value at the P07 qualified-control intake should be eligible for P06.
3. Run `experiment.m` and inspect only baseline stage reachability. Name the owner and unit at each stage.
4. Inspect the separate degree-valued lineage. Treat model truth as a reference, not another path signal.
5. In `interactive.m`, reset and move only ADC resolution from 12 to 6 bits. Observe count, LSB, and error.
6. Read the resolution mechanism, then reset before touching age.
7. Move sample age to exactly 20 ms, then 21 ms. Observe unchanged value and reachability but changed quality.
8. Read the freshness mechanism and state why this is not P11 latency or jitter evidence.
9. Open `B2`, then `B4`; identify the last reached owner and distinguish missing data from received-invalid data.
10. Inject cancellation, timeout, and their tie. Confirm the reached prefix is empty and explain the inherited precedence.
11. Set truth just beyond 180 deg and distinguish saturation error from quantization error.
12. Restore baseline, set age to 21 ms, and select broken value-only evidence. Compare receipt, validity, factual `p06InputEligible`, and the false report.
13. Restore complete evidence and baseline controls to demonstrate stateless recovery.
14. Run `run_checks.m`, answer `checks.md` one prompt at a time, and teach back the trace mechanism and consequence.
