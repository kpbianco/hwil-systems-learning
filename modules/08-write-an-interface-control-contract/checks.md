# Checks: Write an Interface Control Contract

## Observation and interpretation questions

Answer one question after the corresponding view:

1. Which P06 and P07 facts bound the producer and receiver sides without being changed by P08?
2. Why must identity and direction be explicit even when the payload value looks correct?
3. What separate ambiguity does each of version, payload length, and engineering unit remove?
4. Why do exactly -180 and +180 deg pass while +180.001 deg fails?
5. Why can a record be structurally conformant while quality code 0 withholds the scalar?
6. What does the transparent checksum detect, and what security or protocol property does it not prove?
7. Why are sequence limits resource bounds rather than evidence of ordering or synchronized clocks?
8. Why are cancellation and timeout guards instead of elapsed stages in this model?
9. How does a rejected-arrived record differ from a cancelled record that never arrives?
10. Which seven clauses does broken value-only validation ignore?
11. Why does interpreting 0.524 rad as 0.524 deg produce false acceptance and semantic error?
12. Why does receiver release prove neither P06 execution, physical motion, nor achieved safety?

## Independent, negative, and recovery checks

`run_checks.m` independently reconstructs the checksum and verifies clause, two-item envelope-metadata, and
six-field payload identity; fixed resource envelopes; exact baseline payload; signed/zero/inclusive/just-outside angle limits; every
payload-length choice, exact version compatibility, minimum and maximum sequence values, identity mismatch,
unit mismatch, sequence overflow, invalid quality encoding, checksum corruption, valid-but-withheld quality,
cancellation, timeout, tie precedence, event isolation, complete versus value-only decisions, semantic error,
compatible scalar and text inputs, malformed numeric/logical/categorical inputs, call isolation, and exact
recovery.

Timeout and cancellation are already-asserted logical guards. The checks do not measure elapsed time, execute a
protocol, serialize bytes, invoke P06 or P07, access a network/device, or establish physical behavior. Repository
Python tests execute an independently written formula-and-decision oracle plus static source checks; they do not
execute MATLAB.

Rollback is a source-and-manifest operation. The durable Python fixture rolls P08 and every later module back
inside an isolated copy, then proves persisted P08 progress recovers to implemented P07 while completion and
notes remain dormant. It never changes the real learner state or worktree during validation.

## Executable check

Run in MATLAB:

```matlab
run_checks
```

All assertions must pass before learner completion. Static checks cannot substitute for execution in a named
licensed MATLAB runtime.

## Teach-back

In two sentences, answer: “What inputs, observable effects, and failure modes matter when you write an
Interface Control Contract?” State the producer-receiver agreement mechanism first and the system consequence
second.
