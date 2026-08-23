# Lesson: Trace a Measurement Data Path

## Guiding question

What inputs, observable effects, and failure modes matter when you trace a Measurement Data Path?

## From an observed function to a control input

P04 named `Observe position`, P05 fixed that function in hardware, and P06 consumed the scalar
`observedAngleDeg` when it computed command error. P07 fills in the missing logical route without reallocating
those responsibilities or changing that scalar P06 interface:

| Stage | Responsibility | Owner | Output unit |
| --- | --- | --- | --- |
| 1 | Observe position sensor | sensor hardware | V |
| 2 | Digitize sensor voltage | acquisition hardware | count |
| 3 | Calibrate to engineering units | hardware interface | deg |
| 4 | Qualify sample | measurement supervision | deg plus validity |
| 5 | P07 qualified-control intake | control software | deg plus local validity evidence |

The final intake is deliberately P07-local. Reaching it preserves value and quality for an eligibility
decision, but proves neither P06 consumption nor physical sensing hardware, electrical, protocol,
control-response, or safety behavior.

P06 accepts only the scalar `observedAngleDeg`; it has no quality argument. P07 therefore defines
`p06InputEligible = measurementUsable` and exposes a scalar P06 angle only when that Boolean is true. This
adapter does not add a validity input to P06 and does not specify the future P08 interface contract.

## Transparent value lineage

The instructional sensor covers -180 to +180 deg with 0.5 to 4.5 V. Its sensitivity is

```text
S = (4.5 V - 0.5 V) / 360 deg = 1/90 V/deg
sensor_V = clamp(2.5 V + S * true_angle_deg, 0.5 V, 4.5 V)
```

The model's `trueAngleDeg` is a comparison reference. A real measurement path does not receive truth as an
extra channel. If the unclipped voltage is outside the sensor range, `sensorSaturated` records the lost
information even though the clipped voltage remains finite.

For an ADC resolution of `bits`, the acquisition hardware uses the full sensor span:

```text
max_count = 2^bits - 1
adc_count = round((sensor_V - 0.5 V) / 4 V * max_count)
LSB_deg = 360 deg / max_count
```

The hardware interface applies the inverse calibration:

```text
reconstructed_V = 0.5 V + 4 V * adc_count / max_count
angle_deg = (reconstructed_V - 2.5 V) / S
```

For a non-saturated sample, quantization error relative to the sensor-equivalent angle is bounded by one-half
LSB. Saturation error is different: it is information lost before digitization and is not covered by the
quantization bound.

The baseline truth is 30 deg, the sensor output is 2.833333 V, the 12-bit code is 2389 of 4095 counts, and the
calibrated value is about 30.021978 deg. The sample age is 5 ms against a supplied 20 ms freshness limit.

## Reachability and quality

Four adjacent handoffs connect the five stages:

```text
stageReached[1]   = acquisition_entry_permitted
stageReached[i+1] = boundaryCrossed[i]
```

The reached stages are either empty or one contiguous prefix. An already-asserted cancellation or timeout
prevents any sample from entering. Otherwise the first open boundary identifies the last owner that received
the payload.

Qualification asks two factual questions after calibration:

```text
fresh = sample_age_ms <= freshness_limit_ms
quality_valid = NOT sensor_saturated AND fresh
measurement_usable = endpoint_received AND quality_valid
p06_input_eligible = measurement_usable
```

Invalid data still crosses the final P07 boundary with `qualityValid = false`. That is intentional:
**missing**, **received invalid**, **received valid**, and **usable** are different states. P07 traces both the
value and the quality evidence locally, then withholds the scalar P06 adapter output unless the measurement is
usable.

## Lever 1 — ADC resolution

Hold truth at 30 deg, age at 5 ms, and the freshness limit at 20 ms. Sweep 6, 8, 10, and 12 bits. The counts
are 37, 149, 597, and 2389, while the LSB shrinks from about 5.714286 to 0.087912 deg/count. Each observed
quantization residual stays inside half an LSB.

More bits tighten the representable error envelope. They do not change sample age, owner reachability,
saturation, or validity, and they do not guarantee that every arbitrary input's realized error decreases at
every adjacent resolution.

## Lever 2 — supplied sample age

Reset to 12 bits, then sweep age through 0, 10, 20, 21, and 40 ms with a 20 ms limit. Equality passes because
the rule is inclusive. At 21 ms the calibrated value and all boundary crossings remain exactly the same, but
the quality flag becomes invalid, the complete usability result becomes false, and P06 input eligibility is
withheld.

P07 consumes age metadata; it does not derive age from a scheduler, clock, transport, or retry process. P11
later owns latency, deadline, scheduling, and jitter analysis.

## Acquisition cancellation and timeout

Cancellation and timeout are exogenous logical inputs already asserted before acquisition entry. Either one
creates no stage output and no boundary attempt. The combined input preserves the earlier modules' cancellation
precedence and reports `cancelled`.

These event inputs carry no elapsed milliseconds. They do not simulate timeout duration, event ordering in a
runtime, physical safe hold, or recovery timing.

## Deliberately broken evidence boundary

A stale sample can be finite, calibrated, and received at the P07 endpoint while its quality flag is false.
The complete assessment uses value plus quality, reports it unusable, and withholds the scalar P06 input. The
broken `value-only` assessment sees a finite endpoint number, falsely reports usable, and raises `falseUsable`;
it never changes factual `p06InputEligible`.

Assessment mode changes only the report. It cannot alter sensor voltage, ADC count, calibration, reachability,
quality, or factual usability. This is the measurement-path version of “a plausible number is not trustworthy
evidence.”

## Inputs, observables, terminals, and failure modes

- Inputs: model truth reference, ADC resolution, supplied sample age, freshness limit, selected open boundary,
  acquisition-entry event, and usability assessment mode.
- Observable effects: voltage, count, calibrated degrees, LSB and error, saturation, freshness margin, stage
  reachability, boundary attempted/crossed/open state, quality evaluation, endpoint receipt, usability, terminal
  status, reported usability, and false usability.
- Handled terminals: cancellation or timeout before entry, and endpoint delivery with a valid or invalid flag.
  A handled invalid delivery meets the trace contract but is never called usable measurement data.
- Failures: open ownership handoff, sensor saturation, stale sample, combined saturation and staleness, and
  value-only false usability. Malformed or out-of-envelope inputs are rejected before a trace is produced.
- Recovery: the model has no persistent or global state; a fresh valid call after any guard, open handoff,
  invalid sample, broken assessment, or malformed input reproduces the baseline exactly.

## Common mistakes and future boundaries

- Truth reference is not an extra observed signal.
- Volts, counts, degrees, milliseconds, and Booleans must not share an unlabeled axis.
- Received is not valid; valid is not usable until the P07 endpoint receives both value and quality; and only
  usable data is eligible for P06's unchanged scalar input.
- A quantization bound does not cover sensor saturation.
- Boundary names are not P08 schemas, wire formats, checksums, protocols, or electrical contracts.
- Supplied age and injected timeout are not P11 timing, scheduling, retry, or jitter evidence.
- Applying one fixed transparent calibration is not P20 calibration-state management.
- Logical P07 endpoint receipt is neither P06 consumption nor physical sensor, ADC, plant, or control-response
  evidence.

## Completion standard

Localize an entry guard and each open handoff, distinguish voltage/count/degree transformations, explain the
half-LSB bound and freshness equality, diagnose value-only false usability, pass `run_checks.m`, and give a
two-sentence teach-back: trace mechanism first, system consequence second.
