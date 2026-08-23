# Walkthrough: Decompose a System into Functions

1. Read the exact guiding question and carry forward P03's requested angle, authority, position, tolerance, and deadline.
2. Predict once which missing function could make a 45-degree local success untrustworthy after a 70-degree request.
3. Run `experiment.m` and inspect only the baseline position view. Name the request, observed degrees, tolerance, and report time.
4. Open the complementary function-activation view. Follow intent through validation, observation, correction, state update, confirmation, supervision, and reporting.
5. In `interactive.m`, reset and change response fraction only. Observe first tolerance entry and report time move together.
6. Read the lever-one mechanism: the correction function removes a larger fraction of remaining error each update.
7. Select **Reset baseline**, then change confirmation depth only. Observe first entry stay fixed while the report moves.
8. Read the lever-two mechanism: evidence depth belongs to confirmation, not motion generation.
9. Select the broken validation mode and request 70 degrees against 45 degrees of authority. Find the absent validation row.
10. Compare local monitor error with original request error and explain why the success report is false.
11. Restore the complete architecture; exercise rejection, cancellation, and a short deadline one at a time.
12. Reset once more to demonstrate recovery and call isolation, run `run_checks.m`, answer `checks.md`, and teach back the decomposition.
