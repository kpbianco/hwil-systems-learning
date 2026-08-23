# P11 walkthrough: Budget Latency and Jitter

1. Read the exact guiding question and connect P10's dimensionless transition proof to P11's elapsed-time
   allocation.
2. Predict once whether an RSS total can approve while aligned, individually bounded stages miss the deadline.
3. Run `experiment.m`; inspect only the baseline cycle-latency trace and locate the 4.2 ms deadline.
4. Inspect only the cumulative stage envelope; identify which owner contributes each nominal and jitter term.
5. In `interactive.m`, reset and move transport nominal latency from 0.6 through 2.4 ms. Observe margin move
   one-for-one while peak-to-peak jitter stays fixed.
6. Read the nominal-delay mechanism, reset transport to 1.2 ms, and hold deadline, proof, event, and assessment
   fixed.
7. Move jitter scale from 0 through 2. Observe the envelope widen while nominal latency remains 3.3 ms.
8. Read the jitter-allocation mechanism before changing another control.
9. Clear P10 activation proof. Distinguish an available offline plan from unavailable execution evidence.
10. Enable cancellation at 15 ms. Confirm two completed cycles, one started/unfinished cycle, and masked actual
    evidence thereafter.
11. Restore the baseline, set jitter scale to two, and observe timeout at cycle 4's 22.2 ms deadline.
12. Add cancellation at exactly 22.2 ms. Confirm both causes are visible and cancellation has precedence.
13. Read the P10 handoff: SAFE-HOLD is requested, rollback is required, and rollback evidence remains
    unavailable under P10 authority.
14. Restore the baseline to demonstrate stateless recovery after blocked, cancelled, and timed-out calls.
15. At jitter scale two, compare bounded sum with broken RSS. Verify identical planned facts, an RSS false
    approval near 4.075 ms, the additive 4.7 ms bound, and the real timeout symptom.
16. Run `run_checks.m`, answer `checks.md` one prompt at a time, and give the two-sentence mechanism-first
    teach-back.

Elapsed quantities use milliseconds; scheduled cycle and jitter scale are dimensionless. One ideal time base
is not MATLAB-runtime, UI, distributed-clock, bench, HIL, field, or personnel-safety evidence.
