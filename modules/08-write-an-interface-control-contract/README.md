# P08 — Write an Interface Control Contract

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 2:** Allocation and interfaces  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you write an Interface Control Contract?

## Interface-contract mental model

P06 traced a scalar command to a logical latch, and P07 traced a value-plus-quality measurement to a local
qualified intake. Neither lesson defined what independently owned endpoints must agree on. P08 turns one
P07-qualified rotary-angle handoff into an executable promise while leaving P07's gate and P06's scalar
`observedAngleDeg` input unchanged.

The producer and receiver must agree on eight clauses:

1. interface identity and direction;
2. schema version;
3. fixed payload length;
4. engineering unit;
5. inclusive value range;
6. bounded sequence field;
7. quality-code meaning; and
8. record integrity.

The logical record exposes a two-item envelope—declared payload-word count and engineering-unit metadata—plus
six numerical payload fields: interface ID, version, sequence, angle, quality, and checksum. No byte encoding
or physical word width is implied. Its transparent integrity rule covers both envelope metadata items and the
five non-checksum numerical payload fields:

```text
checksum = mod(interface_id + version + payload_words + sequence
               + round(1000 * angle_value) + quality_code + unit_code, 65536)
strict_accept = transfer_attempted AND all(contract_clauses_pass)
input_eligible = strict_accept AND quality_code == 1
```

This arithmetic is intentionally instructional. It makes agreement and corruption visible; it is not a
recommended production checksum or a claim about serialization, protocol, security, or electrical behavior.

## Learning flow

1. Read how P06 and P07 stop at logical handoffs that still need an explicit agreement.
2. Inspect the baseline clause view, then inspect the degree-valued source, record, and receiver view.
3. Move only source angle through the inclusive range and observe acceptance at and beyond the boundary.
4. Reset angle, move only declared payload length, and observe exact shape compatibility.
5. Exercise version, identity, checksum, quality, cancellation, and timeout cases.
6. Break validation by accepting a radian-valued record from its plausible number alone, then recover and run checks.

## Evidence and scope boundaries

- `model.m` — fixed-size deterministic record construction, validation, terminal, and release calculation.
- `experiment.m` — complementary baseline views, two independent sweeps, guarded terminals, and false acceptance.
- `interactive.m` — bounded value, layout, version, sequence, quality, fault, event, validator, and reset controls.
- `lesson.m` and `lesson.md` — concept-first contract clauses, prerequisite connection, and misconception correction.
- `walkthrough.md` — one observation and mechanism transition at a time.
- `checks.md` and `run_checks.m` — independent formulas, limits, malformed inputs, compatibility, isolation, and teach-back.

The model operates on one in-memory logical record. Cancellation and timeout are already-asserted guards with
no elapsed-time behavior. Endpoint acceptance does not prove a byte crossed a wire, a protocol peer executed,
P06 consumed the value, or hardware moved. P09 owns startup/shutdown sequencing, P11 owns latency and jitter,
P12 owns clock synchronization, P13 owns verification-method selection, and P20 owns calibration-state control.
The module uses no random source, external data, file/network/device I/O, Simulink model, or toolbox solver.
