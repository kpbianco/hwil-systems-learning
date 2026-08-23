# Walkthrough: Write a CONOPS from an Operator Goal

1. Read the exact guiding question and the operator goal in `lesson.md`.
2. Predict once: is reaching the physical state sufficient for operator success?
3. Run `experiment.m` and inspect only the baseline event timeline first. Name each event and unit.
4. Inspect the baseline decision-criteria view. Explain why the operator goal is met without safe hold.
5. In `interactive.m`, increase command latency. Observe the physical effect and feedback move together.
6. Read the equation that explains that transition, then select **Reset baseline**.
7. Increase feedback latency. Observe feedback move while the physical-effect time stays fixed.
8. Read the mechanism, then toggle **Feedback available** off to expose the broken observability case.
9. Try cancellation before the command, during the action, and after the effect. State why safety wins a tie.
10. Restore feedback and reset. This fresh baseline is the recovery demonstration; no failed state persists.
11. Run `run_checks.m` and answer the interpretation questions in `checks.md`.
12. Teach back a two-sentence CONOPS: mechanism first, operator consequence second.
