# Lesson: Write an Interface Control Contract

## Guiding question

What inputs, observable effects, and failure modes matter when you write an Interface Control Contract?

## From traced handoffs to explicit agreement

P06 showed that a locally generated correction is not the same fact as receipt at a hardware-side input latch.
P07 showed that a finite measurement is not the same fact as a usable measurement, and exposed a scalar only
after local value-plus-quality qualification. P08 does not add an argument to P06 or rewrite P07. It asks what
the two owners on one logical measurement boundary must agree on before the receiver may release that scalar.

| Contract clause | Producer promise | Receiver check | Baseline |
| --- | --- | --- | --- |
| Identity | emit interface 801 in the declared direction | require interface 801 | pass |
| Version | encode schema version 1 | support version 1 | pass |
| Shape | declare six logical payload words | require exactly six | pass |
| Units | express the angle in degrees | interpret only degrees | pass |
| Range | emit -180 through +180 deg inclusively | reject outside the envelope | pass |
| Sequence | emit an integer from 0 through 65535 | reject outside that resource bound | pass |
| Quality | encode invalid as 0 and valid as 1 | withhold invalid data from P06 | pass |
| Integrity | attach the transparent checksum | independently recompute it | pass |

The direction is P07-qualified producer to a receiver-side P06 scalar adapter. The lesson models a logical
record at that boundary; it does not claim a transport, wire layout, byte order, electrical interface, or
runtime peer.

## Transparent decision rule

The logical record exposes `payload-word-count` and `engineering-unit` as two envelope metadata items, then the
six numerical fields `interface-id`, `schema-version`, `sequence`, `angle`, `quality`, and `checksum`. This
inventory is abstract: it declares observable record elements without claiming byte encoding, alignment, or
physical word width. The intentionally simple checksum covers both envelope metadata items and the five
non-checksum numerical payload fields:

```text
checksum = mod(interface_id + version + payload_words + sequence
               + round(1000 * angle_value) + quality_code + unit_code, 65536)
```

The complete receiver evaluates every clause only after a transfer is permitted:

```text
contract_conformant = transfer_attempted AND all(eight clauses pass)
contract_input_eligible = contract_conformant AND quality_code == 1
```

A conformant record may legitimately carry `quality_code = 0`. The receiver accepts the record structure but
withholds the angle from P06. This preserves P07's distinction between received data and usable data.

## Baseline

The baseline source value is P07's deterministic 12-bit example, approximately 30.021978 deg. Interface 801,
version 1, six words, sequence 42, degree units, valid quality, and checksum 30874 all agree. Every clause passes,
the receiver accepts the record, and the exact scalar is eligible for P06. No conversion occurs in this case.

## Lever 1 — source value against the range contract

Hold every header, quality, and validation choice fixed. Sweep source angle through -180, -90, 0,
30.021978, 180, and 180.001 deg. The inclusive endpoints pass. The just-outside value is finite and the record's
checksum is internally consistent, yet the range clause rejects it and no P06 input is released.

This lever separates numerical plausibility from a declared engineering envelope. It does not repeat P07's
sensor saturation model; P08 receives a logical source value and applies the receiver's interface constraint.

## Lever 2 — payload shape

Reset the source value, then sweep declared payload length through four, five, six, seven, and eight words.
Exactly six passes. A shorter record may omit a required field; a longer record may reflect a different schema.
Neither is made compatible by the other five baseline values remaining plausible.

Shape is a contract fact, not a transport-duration fact. P11 later owns elapsed latency, deadline, retry, and
jitter analysis.

## Compatibility, integrity, and quality

- Version 1 is compatible; versions 0 and 2 are rejected rather than guessed.
- A wrong interface ID is rejected even if every other field matches.
- A one-count checksum corruption is rejected. This checksum exposes the mechanism but is not a security claim.
- Quality code 0 is legal and structurally conformant, but it withholds the scalar.
- Quality code 2 is malformed and rejected because its meaning is undefined.
- Sequence 0 and 65535 are inclusive limits; an injected 65536 is rejected.

These checks show why an Interface Control Contract includes both syntax-like structure and engineering
semantics. Passing only one side is insufficient.

## Cancellation, timeout, and precedence

Cancellation and timeout are exogenous logical inputs already asserted before transfer. Either prevents record
arrival and clause evaluation. Their combined case retains the prerequisite convention that cancellation wins
the reported tie.

The flags contain no milliseconds and model no scheduling, retry, event ordering, or recovery time. Those are
future timing and sequence concerns, not evidence produced by P08.

## Deliberately broken unit validation

Inject `unit-mismatch`. The producer expresses the same physical 30.021978 deg angle as about 0.524 rad and
declares radians, while the receiver contract requires degrees. Complete validation rejects the record at the
unit clause.

The broken `value-only` receiver checks only that the number is finite and inside +/-180. It accepts 0.524,
assumes degrees, and releases a scalar with about -29.498 deg semantic error. The symptoms are
`falseAcceptance`, `falseRelease`, and failed semantic preservation. A plausible magnitude did not preserve
meaning.

## Inputs, observables, terminals, and failure modes

- Inputs: source angle, declared payload length, sender version, sequence, source quality, injected contract
  fault, injected transfer event, and validation mode.
- Observable effects: payload fields, unit, expected/transmitted checksum, per-clause evaluation and pass state,
  range margin, arrival, conformance, receiver decision, input release, semantic error, terminal, and failure.
- Handled terminals: accepted-and-released, accepted-quality-withheld, rejected, cancelled, and timed-out.
- Failures: identity, version, length, unit, range, sequence, quality-code, or checksum disagreement plus
  value-only false acceptance/release. Malformed model inputs are rejected before a record is produced.
- Recovery: the model has no persistent or global state; a valid call after every mismatch, guard, broken
  validator, or malformed input reproduces the exact baseline.

## Common mistakes and future boundaries

- A field name without its owner, direction, unit, range, version, and invalid-data behavior is not a complete contract.
- Arrival is not acceptance; acceptance is not input eligibility when quality is invalid; input release is not P06 execution.
- A checksum can expose accidental corruption but does not prove authenticity, security, or transport correctness.
- Cancellation and timeout inputs do not prove P09 sequence behavior or P11 timing behavior.
- A sequence counter does not prove P12 clock synchronization or packet ordering.
- The fixed degree meaning does not perform P20 calibration-state management.
- Static source inspection and oracle execution in Python do not substitute for MATLAB runtime, protocol, bench, HIL, or field evidence.

## Completion standard

Explain why every baseline clause is needed, predict both inclusive range and exact-length boundaries, diagnose
the unit-mismatch false acceptance, pass `run_checks.m`, and give a two-sentence teach-back: agreement mechanism
first, system consequence second.
