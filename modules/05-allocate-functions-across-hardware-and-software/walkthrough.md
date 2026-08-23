# Walkthrough: Allocate Functions Across Hardware and Software

1. Read the exact guiding question and carry forward P04's ten function names, contracts, and failure observables.
2. Predict once whether software-owned cancellation supervision survives an application-software stall.
3. Run `experiment.m` and inspect only the baseline owner map. Verify one owner per function and identify the fixed physical endpoints.
4. Open the complementary utilization view. State the software and hardware demand, capacity, margin, and units.
5. In `interactive.m`, reset and move the control owner only. Observe software demand fall and hardware demand rise.
6. Read the lever-one mechanism: the two control costs transfer domains without proving timing or physical performance.
7. Select **Reset baseline**, set software to stalled with cancellation injected, then move supervision only.
8. Observe that both choices fit nominal resources, but only hardware-owned supervision retains the cancellation guard and logical safe-hold request; then lower hardware capacity and see that the overloaded owner can no longer supply the guard.
9. Read the lever-two mechanism: supervision must sit outside the application-software fault it is required to contain.
10. Select software supervision and the broken resource-only assessment. Compare full allocation truth with the reported approval.
11. Repeat the fault with the deadline/timeout event, then restore complete evidence and available software to demonstrate recovery.
12. Run `run_checks.m`, answer `checks.md` one prompt at a time, and teach back the allocation mechanism and consequence.
