# Lesson: Build a Closed-Loop Timing Budget

## Guiding question

How do stage delay and jitter determine whether a closed loop meets its timing requirement?

## Mental model

A closed-loop HWIL path is a chain of physical and computational delays. The total latency matters, but its distribution and where uncertainty enters determine whether the loop is trustworthy.

## What to manipulate

Use `interactive.m`. Change one lever at a time before combining effects.

## First observation

Increase one stage delay at a time and watch the total deadline margin shrink. Add jitter and compare the mean latency with the tail that actually causes deadline misses.

## Common mistakes

- Meeting the average timing budget does not guarantee deadline compliance.
- A timing budget without ownership by stage is not actionable.
- Instrumentation can change the path being measured and must be included deliberately.

## Completion standard

The learner can explain the baseline, identify what each lever changes, diagnose the deliberately broken case, and pass `run_checks.m`.
