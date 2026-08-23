from __future__ import annotations

import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P03 = ROOT / "modules/03-define-desired-physical-behavior"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you define "
    "Desired Physical Behavior?"
)
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


def reference_response(
    command_deg: float = 30.0,
    natural_frequency_hz: float = 1.5,
    damping_ratio: float = 0.7,
    command_limit_deg: float = 45.0,
    position_tolerance_deg: float = 0.5,
    velocity_tolerance_deg_s: float = 2.0,
    deadline_ms: float = 1200.0,
    horizon_ms: float = 10000.0,
) -> dict[str, object]:
    """Independent Python oracle for the documented P03 analytic response."""
    sample_ms = 2.0
    times_ms = [
        sample_ms * index for index in range(int(horizon_ms / sample_ms) + 1)
    ]
    omega_n = 2.0 * math.pi * natural_frequency_hz
    effective = max(-command_limit_deg, min(command_deg, command_limit_deg))
    positions: list[float] = []
    velocities: list[float] = []
    for time_ms in times_ms:
        time_s = time_ms / 1000.0
        if damping_ratio == 1.0:
            decay = math.exp(-omega_n * time_s)
            normalized_position = 1.0 - decay * (1.0 + omega_n * time_s)
            normalized_velocity = omega_n**2 * time_s * decay
        else:
            complement = math.sqrt(1.0 - damping_ratio**2)
            omega_d = omega_n * complement
            decay = math.exp(-damping_ratio * omega_n * time_s)
            normalized_position = 1.0 - decay * (
                math.cos(omega_d * time_s)
                + damping_ratio / complement * math.sin(omega_d * time_s)
            )
            normalized_velocity = (
                omega_n
                / complement
                * decay
                * math.sin(omega_d * time_s)
            )
        positions.append(effective * normalized_position)
        velocities.append(effective * normalized_velocity)

    request_mask = [
        abs(command_deg - position) <= position_tolerance_deg
        and abs(velocity) <= velocity_tolerance_deg_s
        for position, velocity in zip(positions, velocities)
    ]
    effective_mask = [
        abs(effective - position) <= position_tolerance_deg
        and abs(velocity) <= velocity_tolerance_deg_s
        for position, velocity in zip(positions, velocities)
    ]

    def sustained_entry(mask: list[bool]) -> float:
        last_outside = max((index for index, value in enumerate(mask) if not value), default=-1)
        first_sustained = last_outside + 1
        return (
            math.inf
            if first_sustained >= len(times_ms)
            else times_ms[first_sustained]
        )

    naive_settling_ms = sustained_entry(request_mask)
    naive_effective_settling_ms = sustained_entry(effective_mask)
    horizon_s = horizon_ms / 1000.0
    if damping_ratio == 1.0:
        future_position_envelope = (
            abs(effective)
            * math.exp(-omega_n * horizon_s)
            * (1.0 + omega_n * horizon_s)
        )
        future_velocity_envelope = (
            abs(effective)
            * omega_n**2
            * horizon_s
            * math.exp(-omega_n * horizon_s)
        )
        future_decay_monotonic = horizon_s >= 1.0 / omega_n
    else:
        complement = math.sqrt(1.0 - damping_ratio**2)
        future_decay_envelope = (
            math.exp(-damping_ratio * omega_n * horizon_s) / complement
        )
        future_position_envelope = abs(effective) * future_decay_envelope
        future_velocity_envelope = abs(effective) * omega_n * future_decay_envelope
        future_decay_monotonic = True
    if effective == 0.0:
        future_decay_monotonic = True
    effective_future_guaranteed = (
        future_decay_monotonic
        and future_position_envelope <= position_tolerance_deg
        and future_velocity_envelope <= velocity_tolerance_deg_s
    )
    request_future_guaranteed = (
        future_decay_monotonic
        and abs(command_deg - effective) + future_position_envelope
        <= position_tolerance_deg
        and future_velocity_envelope <= velocity_tolerance_deg_s
    )
    settling_ms = naive_settling_ms if request_future_guaranteed else math.inf
    effective_settling_ms = (
        naive_effective_settling_ms if effective_future_guaranteed else math.inf
    )
    limited = effective != command_deg
    direction_correct = command_deg == 0 or all(
        position * math.copysign(1.0, command_deg) >= -1e-10
        for position in positions
    )
    settled_by_deadline = settling_ms <= deadline_ms
    requirements_met = not limited and settled_by_deadline and direction_correct
    if limited:
        failure_mode = "command-limited"
    elif not direction_correct:
        failure_mode = "direction-error"
    elif not settled_by_deadline:
        failure_mode = "deadline-missed"
    else:
        failure_mode = "none"
    peak_position = max(abs(position) for position in positions)
    peak_velocity = max(abs(velocity) for velocity in velocities)
    overshoot_deg = max(0.0, peak_position - abs(effective))
    overshoot_percent = 0.0 if effective == 0 else 100.0 * overshoot_deg / abs(effective)
    deadline_index = max(index for index, time in enumerate(times_ms) if time <= deadline_ms)
    return {
        "times_ms": times_ms,
        "positions": positions,
        "velocities": velocities,
        "effective": effective,
        "limited": limited,
        "peak_position": peak_position,
        "peak_velocity": peak_velocity,
        "overshoot_percent": overshoot_percent,
        "settling_ms": settling_ms,
        "naive_settling_ms": naive_settling_ms,
        "effective_settling_ms": effective_settling_ms,
        "settled_by_deadline": settled_by_deadline,
        "effective_settled_by_deadline": effective_settling_ms <= deadline_ms,
        "request_future_guaranteed": request_future_guaranteed,
        "effective_future_guaranteed": effective_future_guaranteed,
        "future_position_envelope": future_position_envelope,
        "future_velocity_envelope": future_velocity_envelope,
        "deadline_sample_ms": times_ms[deadline_index],
        "position_at_deadline": positions[deadline_index],
        "request_error_at_deadline": command_deg - positions[deadline_index],
        "final_error": command_deg - positions[-1],
        "requirements_met": requirements_met,
        "failure_mode": failure_mode,
    }


class P03ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P03")

    def read(self, name: str) -> str:
        return (P03 / name).read_text(encoding="utf-8")

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
                "number": 3,
                "id": "P03",
                "title": "Define Desired Physical Behavior",
                "guiding_question": QUESTION,
                "phase": 1,
                "phase_title": "Mission and behavior",
                "slug": "define-desired-physical-behavior",
                "folder": "modules/03-define-desired-physical-behavior",
                "implementation_batch": "P03",
                "prerequisites": ["P02"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P02"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P03.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_placeholder_residue_and_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            path = P03 / name
            with self.subTest(path=name):
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                lowered = content.lower()
                for residue in ("scaffolded", "activate its governed", "todo", "placeholder"):
                    self.assertNotIn(residue, lowered)

    def test_model_is_transparent_deterministic_presentation_free_and_bounded(self):
        model = self.read("model.m")
        compact = re.sub(r"\s+", " ", model)
        self.assertIn("function out = model(", model)
        self.assertIn("sampleTimeMs = 2", model)
        self.assertIn("horizonMs = 10000", model)
        self.assertIn("maxDeadlineMs = 3000", model)
        self.assertIn("maxCommandMagnitudeDeg = 180", model)
        self.assertIn(
            "effectiveCommandDeg = min(max(commandDeg,-commandLimitDeg),commandLimitDeg);",
            model,
        )
        self.assertRegex(
            compact,
            r"omegaNaturalRadPerSec = 2\*pi\*naturalFrequencyHz;",
        )
        self.assertIn("if dampingRatio == 1", model)
        self.assertIn("sqrt(1 - dampingRatio^2)", model)
        self.assertIn("positionDeg = effectiveCommandDeg*normalizedPosition", model)
        self.assertIn("velocityDegPerSec = effectiveCommandDeg*normalizedVelocityPerSec", model)
        self.assertIn("sustainedEntryTime", model)
        self.assertIn("futurePositionEnvelopeDeg", model)
        self.assertIn("requestFutureGuaranteed", model)
        self.assertIn("deadlineSampleTimeMs", model)
        self.assertIn("settlingTimeMs <= deadlineMs", model)
        self.assertIn("P03:ResourceBound", model)
        self.assertIn("P03:InvalidDampingRatio", model)
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
            "lsim(",
            "tf(",
            "ode45(",
            "sim(",
        ):
            self.assertNotIn(forbidden, model.lower())

    def test_independent_oracle_covers_positive_negative_limits_and_deadline(self):
        baseline = reference_response()
        self.assertAlmostEqual(baseline["peak_position"], 31.3796017948, places=8)
        self.assertAlmostEqual(baseline["peak_velocity"], 129.656854933, places=8)
        self.assertAlmostEqual(baseline["overshoot_percent"], 4.5986726493, places=8)
        self.assertEqual(baseline["settling_ms"], 780.0)
        self.assertTrue(baseline["requirements_met"])
        self.assertEqual(baseline["failure_mode"], "none")

        zero = reference_response(command_deg=0.0)
        self.assertEqual(zero["peak_position"], 0.0)
        self.assertEqual(zero["peak_velocity"], 0.0)
        self.assertEqual(zero["overshoot_percent"], 0.0)
        self.assertEqual(zero["settling_ms"], 0.0)
        slow_critical_zero = reference_response(
            command_deg=0.0, natural_frequency_hz=0.001, damping_ratio=1.0
        )
        self.assertTrue(slow_critical_zero["request_future_guaranteed"])
        self.assertEqual(slow_critical_zero["settling_ms"], 0.0)

        negative = reference_response(command_deg=-30.0)
        self.assertEqual(negative["settling_ms"], baseline["settling_ms"])
        self.assertAlmostEqual(negative["peak_position"], baseline["peak_position"])
        self.assertTrue(
            all(
                abs(positive + mirrored) < 1e-12
                for positive, mirrored in zip(
                    baseline["positions"], negative["positions"]
                )
            )
        )

        deadline_miss = reference_response(deadline_ms=500.0)
        self.assertEqual(deadline_miss["positions"], baseline["positions"])
        self.assertFalse(deadline_miss["settled_by_deadline"])
        self.assertEqual(deadline_miss["failure_mode"], "deadline-missed")

    def test_deadline_boundary_has_executed_behavioral_coverage(self):
        exact_tie = reference_response(deadline_ms=780.0)
        sub_sample_early = reference_response(deadline_ms=779.999)
        non_grid_after = reference_response(deadline_ms=781.0)

        self.assertEqual(exact_tie["settling_ms"], 780.0)
        self.assertTrue(exact_tie["settled_by_deadline"])
        self.assertTrue(exact_tie["requirements_met"])
        self.assertFalse(sub_sample_early["settled_by_deadline"])
        self.assertFalse(sub_sample_early["requirements_met"])
        self.assertEqual(sub_sample_early["failure_mode"], "deadline-missed")
        self.assertEqual(sub_sample_early["deadline_sample_ms"], 778.0)
        self.assertEqual(non_grid_after["deadline_sample_ms"], 780.0)
        self.assertEqual(exact_tie["positions"], sub_sample_early["positions"])
        self.assertEqual(exact_tie["positions"], non_grid_after["positions"])

        checks = self.read("run_checks.m")
        self.assertIn("deadlineTie = model(30,1.5,0.7,45,0.5,2,780);", checks)
        self.assertIn("oneSampleEarly = model(30,1.5,0.7,45,0.5,2,778);", checks)
        self.assertIn("fractionalDeadline = model(30,1.5,0.7,45,0.5,2,781);", checks)

    def test_independent_oracle_covers_both_levers_and_broken_authority(self):
        small = reference_response(command_deg=10.0)
        large = reference_response(command_deg=40.0)
        self.assertAlmostEqual(large["peak_position"] / small["peak_position"], 4.0)
        self.assertAlmostEqual(large["peak_velocity"] / small["peak_velocity"], 4.0)
        self.assertAlmostEqual(large["overshoot_percent"], small["overshoot_percent"])

        low_damping = reference_response(damping_ratio=0.25)
        critical = reference_response(damping_ratio=1.0)
        self.assertGreater(low_damping["overshoot_percent"], 44.0)
        self.assertEqual(critical["overshoot_percent"], 0.0)
        self.assertFalse(low_damping["settled_by_deadline"])
        self.assertTrue(critical["settled_by_deadline"])

        broken = reference_response(command_deg=70.0, command_limit_deg=45.0)
        self.assertEqual(broken["effective"], 45.0)
        self.assertTrue(broken["limited"])
        self.assertTrue(broken["effective_settled_by_deadline"])
        self.assertTrue(math.isinf(broken["settling_ms"]))
        self.assertGreater(broken["final_error"], 24.9)
        self.assertFalse(broken["requirements_met"])
        self.assertEqual(broken["failure_mode"], "command-limited")

        short_trace_trap = reference_response(
            natural_frequency_hz=10.0,
            damping_ratio=0.022,
            deadline_ms=3000.0,
            horizon_ms=3000.0,
        )
        self.assertEqual(short_trace_trap["naive_settling_ms"], 3000.0)
        self.assertFalse(short_trace_trap["request_future_guaranteed"])
        self.assertTrue(math.isinf(short_trace_trap["settling_ms"]))

        bounded_trap = reference_response(
            natural_frequency_hz=10.0,
            damping_ratio=0.022,
            deadline_ms=3000.0,
        )
        self.assertTrue(bounded_trap["request_future_guaranteed"])
        self.assertEqual(bounded_trap["settling_ms"], 4932.0)
        self.assertFalse(bounded_trap["requirements_met"])

    def test_experiment_has_baselines_two_isolated_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sections), 2)
        self.assertIn("commandSweepDeg = [10 20 30 40]", experiment)
        self.assertIn("dampingSweep = [0.25 0.45 0.7 1.0]", experiment)
        self.assertIn("overshootByCommandPercent", experiment)
        self.assertIn("all(diff(overshootByDampingPercent) < 0)", experiment)
        self.assertIn("broken = model(70,1.5,0.7,45,0.5,2,1200)", experiment)
        self.assertIn("Broken assumption", experiment)
        self.assertIn("requested %.1f deg, effective target %.1f deg", experiment)
        self.assertGreaterEqual(experiment.count("figure("), 5)
        self.assertGreaterEqual(experiment.count("xlabel("), 5)
        self.assertGreaterEqual(experiment.count("ylabel("), 6)
        for unit in ("(ms)", "(deg)", "(deg/s)", "(%)", "(-)"):
            self.assertIn(unit, experiment)
        self.assertIn("Mechanism after lever 1", experiment)
        self.assertLess(experiment.index("Mechanism after lever 1"), experiment.index("%% Sweep 2"))
        self.assertLess(
            experiment.index("Mechanism after lever 2"), experiment.index("%% Broken case")
        )

    def test_interactive_controls_are_meaningful_bounded_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        for limits in (
            "'Limits',[-75 75]",
            "'Limits',[0.2 1.0]",
            "'Limits',[0.5 3.0]",
            "'Limits',[20 60]",
            "'Limits',[300 2500]",
        ):
            self.assertIn(limits, interactive)
        self.assertGreaterEqual(interactive.count("ValueChangingFcn"), 5)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 5)
        self.assertIn("resetBaseline", interactive)
        self.assertIn("Requested, effective, and observed position", interactive)
        self.assertIn("Motion must be quiet", interactive)
        self.assertIn("authority margin", interactive)
        self.assertIn("failure: %s", interactive)

    def test_checks_cover_limits_failures_recovery_isolation_and_compatibility(self):
        checks = self.read("run_checks.m")
        self.assertGreaterEqual(checks.count("assert("), 30)
        for marker in (
            "expectedOvershootPercent",
            "smallCommand",
            "largeCommand",
            "lowDamping",
            "criticalDamping",
            "zeroCommand",
            "slowCriticalZero",
            "negativeCommand",
            "exactAuthority",
            "deadlineMiss",
            "deadlineTie",
            "oneSampleEarly",
            "fractionalDeadline",
            "nearCritical",
            "finiteHorizonTrap",
            "brokenAuthority",
            "compatible",
            "int16",
            "single",
            "uint16",
            "P03:InvalidDampingRatio",
            "P03:InvalidTolerance",
            "P03:ResourceBound",
            "afterFailure",
            "afterIsolationProbe",
            "isequaln(baseline,repeat)",
            "sampleCount == 5001",
        ):
            self.assertIn(marker, checks)
        self.assertIn("P03 checks passed", checks)

    def test_lesson_is_concept_first_compounds_on_p02_and_requires_teach_back(self):
        combined = "\n".join(
            self.read(name)
            for name in ("README.md", "lesson.m", "lesson.md", "walkthrough.md", "checks.md")
        )
        self.assertGreaterEqual(combined.count(QUESTION), 3)
        self.assertIn("P02", combined)
        self.assertIn("theta'' + 2*zeta*omega_n*theta'", combined)
        self.assertIn("accepted physical command", combined)
        self.assertIn("position-command authority", combined)
        self.assertIn("position tolerance", combined)
        self.assertIn("velocity tolerance", combined)
        self.assertIn("deadline", combined.lower())
        self.assertIn("failure", combined.lower())
        self.assertIn("recovery", combined.lower())
        self.assertIn("teach-back", combined.lower())
        self.assertIn("Cancellation is intentionally owned", combined)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_retained_evidence_exists_and_states_the_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P03-*.md"))
        self.assertTrue(evidence_files)
        evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence_files)
        for marker in (
            "Acceptance mapping",
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
            "bench",
            "HIL",
            "field",
            "production",
        ):
            self.assertIn(marker, evidence)
        self.assertNotIn("Pending", evidence)
        self.assertRegex(evidence, r"\d+ tests passed")


if __name__ == "__main__":
    unittest.main()
