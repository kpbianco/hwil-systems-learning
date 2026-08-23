# P07 — Trace a Measurement Data Path

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 2:** Allocation and interfaces  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you trace a Measurement Data Path?

## Measurement-path mental model

P05 fixed `Observe position` in hardware, while P06 accepts only the scalar `observedAngleDeg` as a named
command-path input. P07 connects those facts by following one rotary-position observation through five logical
stages without changing P06's interface:

1. sensor hardware maps physical position to voltage;
2. acquisition hardware digitizes voltage to an ADC count;
3. the hardware interface calibrates that count to degrees;
4. measurement supervision qualifies saturation and freshness; and
5. a P07-local qualified-control intake receives the value and its quality evidence.

Only a usable result makes `p06InputEligible = true`; P07 then exposes the one scalar degree value that may be
supplied as P06's `observedAngleDeg`. It does not add a validity input to P06, invoke the P06 model, or define a
P08 interface contract.

The transparent baseline conversions are

```text
sensor_V = clamp(2.5 V + true_angle_deg / 90, 0.5 V, 4.5 V)
adc_count = round((sensor_V - 0.5 V) / 4 V * (2^bits - 1))
angle_deg = -180 deg + adc_count * 360 deg / (2^bits - 1)
fresh = sample_age_ms <= freshness_limit_ms
usable = endpoint_received AND quality_valid
p06_input_eligible = usable
```

The model's true angle is an instructional reference used to expose error; it is not data available to the
measurement chain. A finite engineering value, endpoint receipt, valid quality, and usable observation are
four different facts.

## Learning flow

1. Read how P05's hardware observation becomes eligible for P06's unchanged scalar observed-position input.
2. Inspect baseline reachability, then compare only degree-valued lineage in a separate view.
3. Move only ADC resolution and observe the count, LSB, and half-LSB error bound.
4. Reset resolution, move only supplied sample age, and observe validity change without value or path change.
5. Exercise acquisition cancellation, acquisition timeout, saturation, and each open handoff.
6. Break usability assessment by ignoring a stale quality flag, then recover and run checks.

## Evidence and scope boundaries

- `model.m` — fixed-size, deterministic sensor, ADC, calibration, quality, boundary, and reporting calculation.
- `experiment.m` — complementary baseline views, two independent sweeps, entry guards, saturation, and false usability.
- `interactive.m` — bounded truth, resolution, age, freshness, boundary, event, assessment, and reset controls.
- `lesson.m` and `lesson.md` — concept-first equations, prerequisite connection, and misconception correction.
- `walkthrough.md` — one observation and mechanism transition at a time.
- `checks.md` and `run_checks.m` — independent equations, limits, malformed inputs, guards, isolation, and teach-back.

The endpoint is P07's local qualified-control intake, upstream of P06. Endpoint receipt preserves value and
quality locally; it is not evidence that P06 consumed a value and is not evidence of a physical sensor, ADC,
wire, protocol, control response, or achieved safety. Sample age is supplied metadata and is evaluated only if the
qualification stage is reached; the module does not derive it from elapsed latency. Cancellation and timeout
are already-asserted acquisition guards with no time evolution. P08 owns formal interface contracts, P11 owns
latency, scheduling, retries, and jitter, and P20 owns calibration-state control. This module uses no random
source, external data, file/network/device I/O, Simulink model, or toolbox solver.
