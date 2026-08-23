# Walkthrough: Define Desired Physical Behavior

1. Read the exact guiding question and connect the P02 requested state to this quantitative physical envelope.
2. Predict once whether stopping at 45 degrees satisfies a 70-degree request.
3. Run `experiment.m` and inspect only the baseline position view. Name the command, degrees, tolerance, and deadline.
4. Inspect the complementary velocity view. Explain why position in band is insufficient while motion is not quiet.
5. In `interactive.m`, reset and change command angle only. Observe position and speed scale together.
6. Read the lever-one mechanism; note that normalized overshoot stays fixed in the valid linear envelope.
7. Select **Reset baseline**, then change damping only. Observe overshoot and sustained settling.
8. Read the lever-two mechanism; do not claim that every metric improves monotonically with damping.
9. Run the broken 70-degree request against 45 degrees of command authority. Compare requested and effective target.
10. Shorten the deadline to expose a late-response failure without changing the physical trajectory.
11. Restore the baseline. This fresh result demonstrates stateless recovery and isolation from failed cases.
12. Run `run_checks.m`, answer one interpretation question at a time in `checks.md`, and teach back the behavior contract.
