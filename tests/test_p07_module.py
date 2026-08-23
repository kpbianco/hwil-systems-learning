from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
P07 = ROOT / "modules/07-trace-a-measurement-data-path"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you trace a "
    "Measurement Data Path?"
)
STAGES = [
    "Observe position sensor",
    "Digitize sensor voltage",
    "Calibrate to engineering units",
    "Qualify sample",
    "P07 qualified-control intake",
]
OWNERS = [
    "sensor-hardware",
    "acquisition-hardware",
    "hardware-interface",
    "measurement-supervision",
    "control-software",
]
UNITS = ["V", "count", "deg", "deg", "deg"]
BOUNDARIES = [
    "sensor-to-adc",
    "adc-to-calibration",
    "calibration-to-quality",
    "quality-to-controller",
]
REQUIRED_ARTIFACTS = {
    "README.md",
    "lesson.m",
    "model.m",
    "experiment.m",
    "interactive.m",
    "lesson.md",
    "walkthrough.md",
    "checks.md",
    "run_checks.m",
}


def matlab_round_nonnegative(value: float) -> int:
    """Match MATLAB round for the nonnegative ADC-code domain."""
    return math.floor(value + 0.5)


def reference_trace(
    true_angle: float = 30.0,
    adc_bits: int = 12,
    sample_age: float = 5.0,
    freshness_limit: float = 20.0,
    open_boundary: str = "none",
    event_mode: str = "none",
    assessment_mode: str = "complete",
) -> dict[str, object]:
    """Independent Python oracle for the documented P07 path contract."""
    minimum_sensor_volts = 0.5
    maximum_sensor_volts = 4.5
    zero_sensor_volts = 2.5
    sensor_span_volts = maximum_sensor_volts - minimum_sensor_volts
    sensitivity_volts_per_deg = sensor_span_volts / 360.0
    max_count = 2**adc_bits - 1
    quantization_step = 360.0 / max_count
    freshness_met = False
    freshness_margin = math.nan

    stage_reached = [False] * len(STAGES)
    values = [math.nan] * len(STAGES)
    attempted = [False] * len(BOUNDARIES)
    crossed = [False] * len(BOUNDARIES)
    boundary_open = [open_boundary == name for name in BOUNDARIES]

    cancellation_observed = event_mode in {
        "cancellation",
        "cancellation-timeout-tie",
    }
    timeout_observed = event_mode in {
        "timeout",
        "cancellation-timeout-tie",
    }
    event_observed = cancellation_observed or timeout_observed
    entry_permitted = not event_observed

    unclipped_sensor = math.nan
    sensor_volts = math.nan
    sensor_equivalent = math.nan
    sensor_saturated = False
    adc_count = math.nan
    reconstructed_sensor = math.nan
    calibrated_angle = math.nan
    quantization_error = math.nan
    measurement_error = math.nan
    quality_evaluated = False
    quality_valid = False

    if entry_permitted:
        stage_reached[0] = True
        unclipped_sensor = zero_sensor_volts + sensitivity_volts_per_deg * true_angle
        sensor_volts = min(
            max(unclipped_sensor, minimum_sensor_volts), maximum_sensor_volts
        )
        sensor_saturated = (
            unclipped_sensor < minimum_sensor_volts
            or unclipped_sensor > maximum_sensor_volts
        )
        sensor_equivalent = (
            sensor_volts - zero_sensor_volts
        ) / sensitivity_volts_per_deg
        values[0] = sensor_volts
        attempted[0] = True
        if not boundary_open[0]:
            crossed[0] = True
            stage_reached[1] = True

    if stage_reached[1]:
        ideal_count = (
            (sensor_volts - minimum_sensor_volts) / sensor_span_volts * max_count
        )
        adc_count = matlab_round_nonnegative(ideal_count)
        values[1] = float(adc_count)
        attempted[1] = True
        if not boundary_open[1]:
            crossed[1] = True
            stage_reached[2] = True

    if stage_reached[2]:
        reconstructed_sensor = (
            minimum_sensor_volts + sensor_span_volts * adc_count / max_count
        )
        calibrated_angle = (
            reconstructed_sensor - zero_sensor_volts
        ) / sensitivity_volts_per_deg
        quantization_error = calibrated_angle - sensor_equivalent
        measurement_error = calibrated_angle - true_angle
        values[2] = calibrated_angle
        attempted[2] = True
        if not boundary_open[2]:
            crossed[2] = True
            stage_reached[3] = True

    if stage_reached[3]:
        quality_evaluated = True
        freshness_met = sample_age <= freshness_limit
        freshness_margin = freshness_limit - sample_age
        quality_valid = not sensor_saturated and freshness_met
        values[3] = calibrated_angle
        attempted[3] = True
        if not boundary_open[3]:
            crossed[3] = True
            stage_reached[4] = True
            values[4] = calibrated_angle

    endpoint_received = stage_reached[4]
    endpoint_quality_valid = endpoint_received and quality_valid
    measurement_usable = endpoint_received and endpoint_quality_valid
    payload_preserved = endpoint_received and values[4] == values[3]
    quality_preserved = endpoint_received and endpoint_quality_valid == quality_valid
    p06_input_eligible = measurement_usable
    p06_observed_angle = values[4] if p06_input_eligible else math.nan
    p06_scalar_adapter_met = (
        p06_input_eligible
        and math.isfinite(p06_observed_angle)
        and abs(p06_observed_angle) <= 180
        and p06_observed_angle == values[4]
    ) or (not p06_input_eligible and math.isnan(p06_observed_angle))
    reported_usable = (
        measurement_usable
        if assessment_mode == "complete"
        else endpoint_received and math.isfinite(values[4])
    )
    false_usable = reported_usable and not measurement_usable

    first_open = next(
        (
            index + 1
            for index, (was_attempted, is_open) in enumerate(
                zip(attempted, boundary_open)
            )
            if was_attempted and is_open
        ),
        0,
    )
    deepest = max(
        (index + 1 for index, reached in enumerate(stage_reached) if reached),
        default=0,
    )

    if cancellation_observed:
        terminal = "cancelled"
    elif timeout_observed:
        terminal = "timed-out"
    elif endpoint_received and quality_valid:
        terminal = "delivered-valid"
    elif endpoint_received:
        terminal = "delivered-invalid"
    elif first_open:
        terminal = "boundary-open"
    else:
        terminal = "route-incomplete"

    if terminal == "cancelled":
        failure = "acquisition-cancelled"
    elif terminal == "timed-out":
        failure = "acquisition-timeout"
    elif terminal == "boundary-open":
        failure = BOUNDARIES[first_open - 1]
    elif terminal == "delivered-invalid" and sensor_saturated and not freshness_met:
        failure = "sensor-saturated-and-stale"
    elif terminal == "delivered-invalid" and sensor_saturated:
        failure = "sensor-saturated"
    elif terminal == "delivered-invalid":
        failure = "stale-sample"
    elif terminal == "route-incomplete":
        failure = "internal-route-incomplete"
    else:
        failure = "none"

    trace_contract_met = event_observed or (
        endpoint_received
        and payload_preserved
        and quality_preserved
        and p06_scalar_adapter_met
    )
    return {
        "stage_reached": stage_reached,
        "values": values,
        "attempted": attempted,
        "crossed": crossed,
        "boundary_open": boundary_open,
        "entry_permitted": entry_permitted,
        "event_observed": event_observed,
        "cancellation_observed": cancellation_observed,
        "timeout_observed": timeout_observed,
        "tie_resolved_to_cancellation": event_mode == "cancellation-timeout-tie",
        "unclipped_sensor": unclipped_sensor,
        "sensor_volts": sensor_volts,
        "sensor_equivalent": sensor_equivalent,
        "sensor_saturated": sensor_saturated,
        "adc_count": adc_count,
        "max_count": max_count,
        "reconstructed_sensor": reconstructed_sensor,
        "calibrated_angle": calibrated_angle,
        "quantization_step": quantization_step,
        "quantization_bound": 0.5 * quantization_step,
        "quantization_error": quantization_error,
        "measurement_error": measurement_error,
        "freshness_met": freshness_met,
        "freshness_margin": freshness_margin,
        "quality_evaluated": quality_evaluated,
        "quality_valid": quality_valid,
        "endpoint_received": endpoint_received,
        "endpoint_quality_valid": endpoint_quality_valid,
        "measurement_usable": measurement_usable,
        "payload_preserved": payload_preserved,
        "quality_preserved": quality_preserved,
        "p06_input_eligible": p06_input_eligible,
        "p06_observed_angle": p06_observed_angle,
        "p06_scalar_adapter_met": p06_scalar_adapter_met,
        "reported_usable": reported_usable,
        "false_usable": false_usable,
        "reporting_failure": (
            "value-only-false-usable" if false_usable else "none"
        ),
        "first_open": first_open,
        "deepest": deepest,
        "crossed_count": sum(crossed),
        "terminal": terminal,
        "failure": failure,
        "trace_contract_met": trace_contract_met,
    }


def assert_oracle_invariants(test: unittest.TestCase, result: dict[str, object]) -> None:
    reached = result["stage_reached"]
    crossed = result["crossed"]
    attempted = result["attempted"]
    values = result["values"]
    test.assertEqual(reached[0], result["entry_permitted"])
    test.assertEqual(reached[1:], crossed)
    test.assertTrue(all(not crossed[index] or attempted[index] for index in range(4)))
    test.assertEqual(reached, sorted(reached, reverse=True))
    test.assertTrue(all(math.isfinite(value) for value, active in zip(values, reached) if active))
    test.assertTrue(all(math.isnan(value) for value, active in zip(values, reached) if not active))
    test.assertEqual(result["deepest"], sum(reached))
    test.assertEqual(result["crossed_count"], sum(crossed))
    test.assertEqual(result["quality_evaluated"], reached[3])
    if result["quality_evaluated"]:
        test.assertFalse(math.isnan(result["freshness_margin"]))
    else:
        test.assertFalse(result["freshness_met"])
        test.assertTrue(math.isnan(result["freshness_margin"]))
    test.assertEqual(
        result["measurement_usable"],
        result["endpoint_received"] and result["quality_valid"],
    )
    test.assertEqual(result["p06_input_eligible"], result["measurement_usable"])
    test.assertTrue(result["p06_scalar_adapter_met"])
    if result["p06_input_eligible"]:
        test.assertEqual(result["p06_observed_angle"], values[4])
        test.assertLessEqual(abs(result["p06_observed_angle"]), 180)
    else:
        test.assertTrue(math.isnan(result["p06_observed_angle"]))
    if reached[1]:
        test.assertEqual(result["adc_count"], int(result["adc_count"]))
        test.assertGreaterEqual(result["adc_count"], 0)
        test.assertLessEqual(result["adc_count"], result["max_count"])
    if reached[2]:
        test.assertLessEqual(
            abs(result["quantization_error"]),
            result["quantization_bound"] + 1e-12,
        )
    if result["endpoint_received"]:
        test.assertTrue(result["payload_preserved"])
        test.assertTrue(result["quality_preserved"])


class P07ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P07")

    def read(self, name: str) -> str:
        return (P07 / name).read_text(encoding="utf-8")

    def test_permanent_identity_prerequisite_and_complete_artifact_set(self):
        self.assertEqual(
            {
                "number": self.module["number"],
                "id": self.module["id"],
                "title": self.module["title"],
                "guiding_question": self.module["guiding_question"],
                "phase": self.module["phase"],
                "phase_title": self.module["phase_title"],
                "slug": self.module["slug"],
                "folder": self.module["folder"],
                "implementation_batch": self.module["implementation_batch"],
                "prerequisites": self.module["prerequisites"],
            },
            {
                "number": 7,
                "id": "P07",
                "title": "Trace a Measurement Data Path",
                "guiding_question": QUESTION,
                "phase": 2,
                "phase_title": "Allocation and interfaces",
                "slug": "trace-a-measurement-data-path",
                "folder": "modules/07-trace-a-measurement-data-path",
                "implementation_batch": "P07",
                "prerequisites": ["P06"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P06"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P07.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_residue_and_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            with self.subTest(path=name):
                content = self.read(name)
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                lowered = content.lower()
                for residue in ("scaffolded", "activate its governed", "todo", "placeholder"):
                    self.assertNotIn(residue, lowered)

    def test_model_is_transparent_presentation_free_and_resource_bounded(self):
        model = self.read("model.m")
        compact = re.sub(r"\s+|\.\.\.", "", model)
        self.assertIn("function out = model(", model)
        self.assertIn("sensorFullScaleAngleDeg = 180", model)
        self.assertIn("maxPhysicalAngleDeg = 360", model)
        self.assertIn("minimumAdcBits = 4", model)
        self.assertIn("maximumAdcBits = 16", model)
        self.assertIn("maxAgeMs = 10000", model)
        for fragment in (
            "unclippedSensorVolts=sensorZeroVolts+sensorSensitivityVoltsPerDeg*trueAngleDeg;",
            "sensorSaturated=unclippedSensorVolts<sensorMinimumVolts||unclippedSensorVolts>sensorMaximumVolts;",
            "adcCount=round((sensorVolts-sensorMinimumVolts)/sensorSpanVolts*maxAdcCount);",
            "calibratedAngleDeg=(reconstructedSensorVolts-sensorZeroVolts)/sensorSensitivityVoltsPerDeg;",
            "freshnessCriterionMet=false;",
            "freshnessMarginMs=NaN;",
            "freshnessCriterionMet=sampleAgeMs<=freshnessLimitMs;",
            "qualityValid=~sensorSaturated&&freshnessCriterionMet;",
            "p06InputEligible=measurementUsable;",
            "p06ObservedAngleDeg=stageOutputValue(5);",
            "reportedUsable=measurementUsable;",
            "reportedUsable=endpointReceived&&isfinite(stageOutputValue(5));",
            "falseUsable=reportedUsable&&~measurementUsable;",
        ):
            self.assertIn(fragment, compact)
        self.assertGreater(
            model.index("freshnessCriterionMet = sampleAgeMs <= freshnessLimitMs"),
            model.index("if stageReached(4)"),
        )
        self.assertIn("stageReached(2:end)", self.read("run_checks.m"))
        for error_id in (
            "P07:InvalidAngle",
            "P07:InvalidAdcBits",
            "P07:InvalidSampleAge",
            "P07:InvalidFreshnessLimit",
            "P07:InvalidBoundary",
            "P07:InvalidEventMode",
            "P07:InvalidAssessmentMode",
        ):
            self.assertIn(error_id, model)
        for forbidden in (
            "figure(",
            "plot(",
            "uifigure(",
            "rng(",
            "rand(",
            "randn(",
            "persistent ",
            "global ",
            "fopen(",
            "webread(",
            "serialport(",
            "tcpclient(",
            "udpport(",
            "eval(",
            "sim(",
            "intlinprog(",
            "optimproblem(",
            "fmincon(",
            "ga(",
        ):
            self.assertNotIn(forbidden, model.lower())

    def test_independent_oracle_baseline_signed_and_sensor_limits(self):
        self.assertEqual(matlab_round_nonnegative(2.5), 3)
        baseline = reference_trace()
        assert_oracle_invariants(self, baseline)
        self.assertAlmostEqual(baseline["sensor_volts"], 2.833333333333333)
        self.assertEqual(baseline["adc_count"], 2389)
        self.assertEqual(baseline["max_count"], 4095)
        self.assertAlmostEqual(baseline["calibrated_angle"], 30.021978021978)
        self.assertAlmostEqual(baseline["measurement_error"], 0.021978021978)
        self.assertAlmostEqual(baseline["quantization_step"], 360 / 4095)
        self.assertEqual(baseline["freshness_margin"], 15)
        self.assertTrue(baseline["quality_valid"])
        self.assertTrue(baseline["measurement_usable"])
        self.assertTrue(baseline["trace_contract_met"])
        self.assertEqual(baseline["terminal"], "delivered-valid")

        zero = reference_trace(true_angle=0)
        negative = reference_trace(true_angle=-30)
        negative_full_scale = reference_trace(true_angle=-180)
        positive_full_scale = reference_trace(true_angle=180)
        negative_just_outside = reference_trace(true_angle=-180.001)
        negative_maximum = reference_trace(true_angle=-360)
        just_outside = reference_trace(true_angle=180.001)
        maximum = reference_trace(true_angle=360)
        for result in (
            zero,
            negative,
            negative_full_scale,
            positive_full_scale,
            negative_just_outside,
            negative_maximum,
            just_outside,
            maximum,
        ):
            assert_oracle_invariants(self, result)
        self.assertLessEqual(abs(zero["quantization_error"]), zero["quantization_bound"])
        self.assertAlmostEqual(negative["calibrated_angle"], -baseline["calibrated_angle"])
        self.assertEqual((negative_full_scale["adc_count"], negative_full_scale["calibrated_angle"]), (0, -180.0))
        self.assertEqual((positive_full_scale["adc_count"], positive_full_scale["calibrated_angle"]), (4095, 180.0))
        self.assertFalse(negative_full_scale["sensor_saturated"])
        self.assertFalse(positive_full_scale["sensor_saturated"])
        for saturated in (
            negative_just_outside,
            negative_maximum,
            just_outside,
            maximum,
        ):
            self.assertTrue(saturated["endpoint_received"])
            self.assertTrue(saturated["sensor_saturated"])
            self.assertFalse(saturated["quality_valid"])
            self.assertFalse(saturated["measurement_usable"])
            self.assertFalse(saturated["p06_input_eligible"])
            self.assertEqual(saturated["terminal"], "delivered-invalid")
            self.assertEqual(saturated["failure"], "sensor-saturated")
        self.assertEqual(negative_just_outside["adc_count"], 0)
        self.assertEqual(negative_maximum["calibrated_angle"], -180)

    def test_independent_oracle_adc_sweep_and_resource_limits(self):
        choices = [6, 8, 10, 12]
        expected_counts = [37, 149, 597, 2389]
        results = [reference_trace(adc_bits=bits) for bits in choices]
        self.assertEqual([result["adc_count"] for result in results], expected_counts)
        self.assertTrue(
            all(
                results[index + 1]["quantization_step"] < results[index]["quantization_step"]
                for index in range(len(results) - 1)
            )
        )
        for result in results:
            assert_oracle_invariants(self, result)
            self.assertLessEqual(
                abs(result["quantization_error"]), result["quantization_bound"] + 1e-12
            )
            self.assertTrue(result["quality_valid"])

        minimum = reference_trace(adc_bits=4)
        maximum = reference_trace(adc_bits=16)
        self.assertEqual(minimum["max_count"], 15)
        self.assertEqual(maximum["max_count"], 65535)
        self.assertGreater(minimum["quantization_step"], maximum["quantization_step"])
        self.assertLessEqual(minimum["adc_count"], minimum["max_count"])
        self.assertLessEqual(maximum["adc_count"], maximum["max_count"])

    def test_independent_oracle_freshness_boundary_changes_quality_only(self):
        ages = [0, 10, 20, 21, 40]
        results = [reference_trace(sample_age=age, freshness_limit=20) for age in ages]
        self.assertEqual(
            [result["freshness_met"] for result in results],
            [True, True, True, False, False],
        )
        self.assertEqual(
            [result["measurement_usable"] for result in results],
            [True, True, True, False, False],
        )
        self.assertTrue(all(result["endpoint_received"] for result in results))
        self.assertEqual(
            [result["calibrated_angle"] for result in results],
            [results[0]["calibrated_angle"]] * len(results),
        )
        exact_zero = reference_trace(sample_age=0, freshness_limit=0)
        just_over_zero = reference_trace(sample_age=0.001, freshness_limit=0)
        maximum_equal = reference_trace(sample_age=10000, freshness_limit=10000)
        self.assertTrue(exact_zero["measurement_usable"])
        self.assertFalse(just_over_zero["measurement_usable"])
        self.assertTrue(maximum_equal["measurement_usable"])
        self.assertEqual(results[2]["freshness_margin"], 0)
        self.assertEqual(results[3]["failure"], "stale-sample")

    def test_independent_oracle_all_boundaries_and_entry_event_isolation(self):
        for index, boundary in enumerate(BOUNDARIES, start=1):
            with self.subTest(boundary=boundary):
                result = reference_trace(open_boundary=boundary)
                assert_oracle_invariants(self, result)
                self.assertEqual(result["first_open"], index)
                self.assertEqual(result["deepest"], index)
                self.assertEqual(result["crossed_count"], index - 1)
                self.assertEqual(result["terminal"], "boundary-open")
                self.assertEqual(result["failure"], boundary)
                self.assertFalse(result["endpoint_received"])
                self.assertFalse(result["trace_contract_met"])

        cancelled = reference_trace(event_mode="cancellation")
        timed_out = reference_trace(event_mode="timeout")
        tied = reference_trace(event_mode="cancellation-timeout-tie")
        event_before_open = reference_trace(
            open_boundary="sensor-to-adc", event_mode="timeout"
        )
        for result in (cancelled, timed_out, tied, event_before_open):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["event_observed"])
            self.assertFalse(result["entry_permitted"])
            self.assertFalse(any(result["stage_reached"]))
            self.assertFalse(any(result["attempted"]))
            self.assertFalse(result["quality_evaluated"])
            self.assertFalse(result["freshness_met"])
            self.assertTrue(math.isnan(result["freshness_margin"]))
            self.assertFalse(result["endpoint_received"])
            self.assertTrue(result["trace_contract_met"])
        self.assertEqual(cancelled["terminal"], "cancelled")
        self.assertEqual(timed_out["terminal"], "timed-out")
        self.assertTrue(tied["tie_resolved_to_cancellation"])
        self.assertEqual(tied["terminal"], "cancelled")
        self.assertEqual(event_before_open["first_open"], 0)
        self.assertEqual(event_before_open["terminal"], "timed-out")

    def test_independent_oracle_invalid_delivery_and_broken_report_isolation(self):
        stale = reference_trace(sample_age=21)
        broken = reference_trace(sample_age=21, assessment_mode="value-only")
        saturated = reference_trace(true_angle=181)
        saturated_broken = reference_trace(
            true_angle=181, assessment_mode="value-only"
        )
        saturated_and_stale = reference_trace(true_angle=181, sample_age=21)
        saturated_and_stale_broken = reference_trace(
            true_angle=181, sample_age=21, assessment_mode="value-only"
        )
        for factual_key in (
            "stage_reached",
            "values",
            "attempted",
            "crossed",
            "boundary_open",
            "sensor_volts",
            "adc_count",
            "calibrated_angle",
            "quality_evaluated",
            "quality_valid",
            "endpoint_received",
            "measurement_usable",
            "terminal",
            "failure",
            "trace_contract_met",
        ):
            self.assertEqual(stale[factual_key], broken[factual_key])
        self.assertTrue(stale["endpoint_received"])
        self.assertFalse(stale["quality_valid"])
        self.assertFalse(stale["measurement_usable"])
        self.assertFalse(stale["reported_usable"])
        self.assertTrue(broken["reported_usable"])
        self.assertTrue(broken["false_usable"])
        self.assertEqual(broken["reporting_failure"], "value-only-false-usable")
        self.assertEqual(saturated_and_stale["failure"], "sensor-saturated-and-stale")

        for complete, value_only in (
            (saturated, saturated_broken),
            (saturated_and_stale, saturated_and_stale_broken),
        ):
            for factual_key in (
                "stage_reached",
                "values",
                "attempted",
                "crossed",
                "sensor_saturated",
                "quality_valid",
                "endpoint_received",
                "measurement_usable",
                "p06_input_eligible",
                "p06_observed_angle",
                "terminal",
                "failure",
                "trace_contract_met",
            ):
                if factual_key == "p06_observed_angle":
                    self.assertTrue(math.isnan(complete[factual_key]))
                    self.assertTrue(math.isnan(value_only[factual_key]))
                else:
                    self.assertEqual(complete[factual_key], value_only[factual_key])
            self.assertFalse(complete["reported_usable"])
            self.assertTrue(value_only["reported_usable"])
            self.assertTrue(value_only["false_usable"])
            self.assertEqual(
                value_only["reporting_failure"], "value-only-false-usable"
            )

        missing = reference_trace(
            sample_age=21,
            open_boundary="quality-to-controller",
            assessment_mode="value-only",
        )
        self.assertTrue(missing["quality_evaluated"])
        self.assertFalse(missing["quality_valid"])
        self.assertFalse(missing["endpoint_received"])
        self.assertFalse(missing["reported_usable"])
        self.assertFalse(missing["false_usable"])
        self.assertEqual(missing["terminal"], "boundary-open")

    def test_every_supported_terminal_is_behaviorally_reachable(self):
        scenarios = [
            reference_trace(),
            reference_trace(sample_age=21),
            reference_trace(event_mode="cancellation"),
            reference_trace(event_mode="timeout"),
            reference_trace(open_boundary="sensor-to-adc"),
        ]
        self.assertEqual(
            {scenario["terminal"] for scenario in scenarios},
            {
                "delivered-valid",
                "delivered-invalid",
                "cancelled",
                "timed-out",
                "boundary-open",
            },
        )

    def test_experiment_has_ordered_baselines_two_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sweep_sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sweep_sections), 2)
        for marker in (
            "adcBitSweep = [6 8 10 12]",
            "sampleAgeSweepMs = [0 10 20 21 40]",
            "isequal(adcCountByBits,[37 149 597 2389])",
            "isequal(freshByAge,[true true true false false])",
            "cancellation-timeout-tie",
            "sensor-saturated",
            "value-only",
            "broken.falseUsable",
            "isequaln(recovered,baseline)",
        ):
            self.assertIn(marker, experiment)
        self.assertLess(
            experiment.index("Mechanism after lever 1"), experiment.index("%% Sweep 2")
        )
        self.assertLess(
            experiment.index("Mechanism after lever 2"), experiment.index("%% Broken case")
        )
        self.assertGreaterEqual(experiment.count("figure("), 5)
        for unit in (" V", " count", "(deg)", "(bit)", "(ms)", "Boolean -"):
            self.assertIn(unit, experiment)
        self.assertIn("P08 owns interface contracts", experiment)
        self.assertIn("P11 timing and jitter", experiment)
        self.assertIn("P20 calibration-state control", experiment)

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertGreaterEqual(interactive.count("uispinner"), 4)
        self.assertGreaterEqual(interactive.count("uidropdown"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 7)
        for limits in (
            "'Limits',[-360 360]",
            "'Limits',[4 16]",
            "'Limits',[0 100]",
        ):
            self.assertIn(limits, interactive)
        self.assertIn("openBoundary.ItemsData", interactive)
        self.assertIn("cancellation-timeout-tie", interactive)
        self.assertIn("assessmentMode.ItemsData = {'complete','value-only'}", interactive)
        self.assertIn("resetBaseline", interactive)
        for marker in (
            "trueAngle.Value = 30",
            "adcBits.Value = 12",
            "sampleAge.Value = 5",
            "freshnessLimit.Value = 20",
            "openBoundary.Value = 'none'",
            "eventMode.Value = 'none'",
            "assessmentMode.Value = 'complete'",
        ):
            self.assertIn(marker, interactive)
        self.assertIn("Stage reached (Boolean -)", interactive)
        self.assertIn("Position (deg)", interactive)
        self.assertIn("measurement usable", interactive)
        self.assertIn("false usable", interactive)

    def test_checks_cover_failures_recovery_compatibility_and_bounds(self):
        checks = self.read("run_checks.m")
        for marker in (
            "expectedStageNames",
            "expectedStageOwners",
            "expectedStageUnits",
            "expectedBoundaryNames",
            "adcBitChoices",
            "minimumResolution",
            "maximumResolution",
            "zeroAngle",
            "negativeAngle",
            "negativeFullScale",
            "positiveFullScale",
            "justSaturated",
            "maxBounded",
            "negativeJustSaturated",
            "negativeMaxBounded",
            "model(-360.001",
            "ageAtLimit",
            "ageJustOver",
            "zeroAgeZeroLimit",
            "maxAgeAtLimit",
            "boundaryChoices",
            "cancelled",
            "timedOut",
            "tied",
            "eventBeforeBoundary",
            "saturatedAndStale",
            "brokenValueOnly",
            "saturatedValueOnly",
            "saturatedAndStaleValueOnly",
            "missingValueOnly",
            "p06InputEligible",
            "p06ObservedAngleDeg",
            "string(' NONE ')",
            "P07:InvalidAngle",
            "P07:InvalidAdcBits",
            "P07:InvalidSampleAge",
            "P07:InvalidFreshnessLimit",
            "P07:InvalidBoundary",
            "P07:InvalidEventMode",
            "P07:InvalidAssessmentMode",
            "afterMalformed",
            "assertTraceInvariant",
            "P07 checks passed",
        ):
            self.assertIn(marker, checks)

    def test_lesson_is_concept_first_compounds_and_preserves_boundaries(self):
        combined = "\n".join(
            self.read(name)
            for name in ("README.md", "lesson.m", "lesson.md", "walkthrough.md", "checks.md")
        )
        self.assertGreaterEqual(combined.count(QUESTION), 3)
        for marker in (
            "P04",
            "P05",
            "P06",
            "P08",
            "P11",
            "P20",
            "Observe position",
            "voltage",
            "count",
            "quality",
            "input",
            "observable",
            "failure",
            "cancellation",
            "timeout",
            "recovery",
            "interpretation",
            "teach-back",
            "deg/count",
        ):
            self.assertIn(marker.lower(), combined.lower())
        flattened = re.sub(r"\s+", " ", combined)
        self.assertIn("not data available to the measurement chain", flattened)
        self.assertIn("not evidence of a physical sensor", flattened)
        self.assertIn("not P11 timing", flattened)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_p06_compatibility_keeps_scalar_input_and_gates_it_upstream(self):
        p06_model = (
            ROOT / "modules/06-trace-a-command-path/model.m"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            p06_model,
            r"function out = model\(requestedAngleDeg,observedAngleDeg,",
        )
        self.assertIn(
            "observedAngleDeg = normalizeBoundedScalar", p06_model
        )
        self.assertNotIn("qualityValid", p06_model)

        combined = "\n".join(
            self.read(name)
            for name in ("README.md", "lesson.m", "lesson.md", "checks.md")
        )
        for marker in (
            "observedAngleDeg",
            "P06 accepts only the scalar",
            "p06InputEligible",
            "does not add a validity input to P06",
        ):
            self.assertIn(marker, combined)

    def test_rollback_fixture_recovers_persisted_p07_to_p06(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 7:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            (state_dir / "progress.json").write_text(
                json.dumps({"current": "P07", "completed": {}, "notes": {}}) + "\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            recovered = subprocess.run(
                [str(fixture / "bin/learn"), "continue"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn("P06 — Trace a Command Path", recovered.stdout)
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P06")

    def test_rollback_hides_unavailable_completion_without_erasing_progress(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 7:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            retained_note = "P07 teach-back retained across source rollback"
            (state_dir / "progress.json").write_text(
                json.dumps(
                    {
                        "current": "P07",
                        "completed": {"P07": True},
                        "notes": {"P07": retained_note},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"

            recovered = subprocess.run(
                [str(fixture / "bin/learn"), "continue"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            status = subprocess.run(
                [str(fixture / "bin/learn"), "status"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            listing = subprocess.run(
                [str(fixture / "bin/learn"), "list"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )

            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn("P06 — Trace a Command Path", recovered.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("24 total, 6 implemented, 0 completed", status.stdout)
            self.assertEqual(listing.returncode, 0, listing.stderr)
            p07_line = next(
                line for line in listing.stdout.splitlines() if " P07 " in line
            )
            self.assertTrue(p07_line.startswith("○ P07"), p07_line)
            self.assertNotIn("✓ P07", listing.stdout)

            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P06")
            self.assertTrue(state["completed"]["P07"])
            self.assertEqual(state["notes"]["P07"], retained_note)

    def test_retained_evidence_has_required_sections_and_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P07-*.md"))
        self.assertTrue(evidence_files)
        evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence_files)
        for marker in (
            "Acceptance mapping",
            "Exact commands and results",
            "Figure, control, metric, and unit inventory",
            "Changed invariants",
            "Preserved invariants",
            "Residual risks",
            "Rollback",
            "Unperformed validation",
            "Static",
            "MATLAB runtime",
            "UI",
            "numerical fidelity",
            "protocol",
            "bench",
            "HIL",
            "field",
            "RT1/RT2",
            "Unreal",
            "signing",
            "deployment",
            "production",
        ):
            self.assertIn(marker, evidence)


if __name__ == "__main__":
    unittest.main()
