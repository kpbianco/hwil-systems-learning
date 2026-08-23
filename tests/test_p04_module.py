from __future__ import annotations

import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P04 = ROOT / "modules/04-decompose-a-system-into-functions"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you decompose "
    "a System into Functions?"
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


def reference_chain(
    request_deg: float = 30.0,
    response_fraction: float = 0.35,
    confirmation_samples: int = 3,
    authority_deg: float = 45.0,
    tolerance_deg: float = 0.5,
    deadline_ms: float = 1000.0,
    cancel_at_ms: float = math.inf,
    architecture_mode: str = "complete",
) -> dict[str, object]:
    """Independent Python oracle for the documented P04 recurrence and guards."""
    sample_ms = 20.0
    times_ms = [float(value) for value in range(0, 3001, 20)]
    positions = [0.0] * len(times_ms)
    corrections = [0.0] * len(times_ms)
    authority_valid = abs(request_deg) <= authority_deg
    bypassed = architecture_mode == "bypass-validation"
    effective_target = max(-authority_deg, min(request_deg, authority_deg))
    monitor_target = effective_target if bypassed else request_deg
    streak = 0
    completion_ms = math.inf
    cancel_observed_ms = math.inf

    if not bypassed and not authority_valid:
        terminal_index = 0
        status = "rejected"
    else:
        status = "active"
        terminal_index = -1
        for index, time_ms in enumerate(times_ms):
            if time_ms >= cancel_at_ms:
                status = "cancelled"
                terminal_index = index
                cancel_observed_ms = time_ms
                break
            if abs(monitor_target - positions[index]) <= tolerance_deg:
                streak += 1
            else:
                streak = 0
            if streak >= confirmation_samples:
                status = "completed"
                terminal_index = index
                completion_ms = time_ms
                break
            if time_ms >= deadline_ms:
                status = "deadline-missed"
                terminal_index = index
                break
            corrections[index] = response_fraction * (
                effective_target - positions[index]
            )
            positions[index + 1] = positions[index] + corrections[index]

    for index in range(terminal_index + 1, len(positions)):
        positions[index] = positions[terminal_index]
    request_errors = [request_deg - position for position in positions]
    monitor_errors = [monitor_target - position for position in positions]

    def first_within(errors: list[float]) -> float:
        return next(
            (
                times_ms[index]
                for index, value in enumerate(errors)
                if abs(value) <= tolerance_deg
            ),
            math.inf,
        )

    report_ms = times_ms[terminal_index]
    reported_success = status == "completed"
    request_satisfied = abs(request_errors[terminal_index]) <= tolerance_deg
    false_success = reported_success and not request_satisfied
    request_goal_met = (
        reported_success
        and authority_valid
        and request_satisfied
        and not bypassed
    )
    if false_success:
        failure_mode = "intent-lost"
    elif bypassed:
        failure_mode = "validation-bypassed"
    elif status == "rejected":
        failure_mode = "request-rejected"
    elif status == "cancelled":
        failure_mode = "cancelled"
    elif status == "deadline-missed":
        failure_mode = "deadline-missed"
    else:
        failure_mode = "none"
    return {
        "times_ms": times_ms,
        "positions": positions,
        "corrections": corrections,
        "effective_target": effective_target,
        "monitor_target": monitor_target,
        "authority_valid": authority_valid,
        "status": status,
        "failure_mode": failure_mode,
        "report_ms": report_ms,
        "completion_ms": completion_ms,
        "cancel_observed_ms": cancel_observed_ms,
        "position_at_report": positions[terminal_index],
        "request_error_at_report": request_errors[terminal_index],
        "monitor_error_at_report": monitor_errors[terminal_index],
        "first_request_entry_ms": first_within(request_errors),
        "first_monitor_entry_ms": first_within(monitor_errors),
        "reported_success": reported_success,
        "request_goal_met": request_goal_met,
        "false_success": false_success,
        "safe_hold": status in {"rejected", "cancelled", "deadline-missed"},
        "physical_motion": any(
            abs(positions[index + 1] - positions[index]) > 1e-12
            for index in range(len(positions) - 1)
        ),
        "terminal_index": terminal_index,
    }


class P04ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P04")

    def read(self, name: str) -> str:
        return (P04 / name).read_text(encoding="utf-8")

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
                "number": 4,
                "id": "P04",
                "title": "Decompose a System into Functions",
                "guiding_question": QUESTION,
                "phase": 1,
                "phase_title": "Mission and behavior",
                "slug": "decompose-a-system-into-functions",
                "folder": "modules/04-decompose-a-system-into-functions",
                "implementation_batch": "P04",
                "prerequisites": ["P03"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P03"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P04.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_residue_and_exactly_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            path = P04 / name
            with self.subTest(path=name):
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                lowered = content.lower()
                for residue in (
                    "scaffolded",
                    "activate its governed",
                    "todo",
                    "placeholder",
                ):
                    self.assertNotIn(residue, lowered)

    def test_model_is_transparent_presentation_free_and_resource_bounded(self):
        model = self.read("model.m")
        compact = re.sub(r"\s+", " ", model)
        self.assertIn("function out = model(", model)
        self.assertIn("sampleTimeMs = 20", model)
        self.assertIn("horizonMs = 3000", model)
        self.assertIn("maxConfirmationSamples = 20", model)
        self.assertRegex(
            compact,
            r"correctionDeg\(k\) = responseFraction\*\(effectiveTargetDeg - positionDeg\(k\)\);",
        )
        self.assertIn(
            "positionDeg(k+1) = positionDeg(k) + correctionDeg(k);", model
        )
        self.assertIn("functionActivation = false(sampleCount,functionCount)", model)
        self.assertIn("functionInputs", model)
        self.assertIn("functionOutputs", model)
        self.assertIn("functionFailureModes", model)
        self.assertIn("P04:InvalidDeadlineGrid", model)
        self.assertIn("P04:InvalidCancelTime", model)
        self.assertIn("P04:InvalidArchitecture", model)
        self.assertIn("P04:ResourceBound", model)
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

    def test_independent_oracle_covers_recurrence_and_limiting_cases(self):
        baseline = reference_chain()
        expected_position = 30.0 * (1.0 - (1.0 - 0.35) ** 12)
        self.assertEqual(baseline["first_request_entry_ms"], 200.0)
        self.assertEqual(baseline["report_ms"], 240.0)
        self.assertAlmostEqual(baseline["position_at_report"], expected_position)
        self.assertAlmostEqual(baseline["request_error_at_report"], 0.170640271893)
        self.assertTrue(baseline["request_goal_met"])
        self.assertEqual(baseline["failure_mode"], "none")

        zero_response = reference_chain(response_fraction=0.0, deadline_ms=100.0)
        unity_response = reference_chain(response_fraction=1.0)
        zero_request = reference_chain(request_deg=0.0)
        negative = reference_chain(request_deg=-30.0)
        self.assertFalse(zero_response["physical_motion"])
        self.assertEqual(zero_response["status"], "deadline-missed")
        self.assertEqual(unity_response["report_ms"], 60.0)
        self.assertEqual(unity_response["position_at_report"], 30.0)
        self.assertFalse(zero_request["physical_motion"])
        self.assertEqual(zero_request["report_ms"], 40.0)
        self.assertEqual(negative["report_ms"], baseline["report_ms"])
        self.assertTrue(
            all(
                abs(positive + mirrored) < 1e-12
                for positive, mirrored in zip(
                    baseline["positions"], negative["positions"]
                )
            )
        )

    def test_independent_oracle_covers_both_levers_and_broken_intent(self):
        slow = reference_chain(response_fraction=0.20)
        fast = reference_chain(response_fraction=0.70)
        self.assertEqual(slow["report_ms"], 420.0)
        self.assertEqual(fast["report_ms"], 120.0)

        shallow = reference_chain(confirmation_samples=1)
        deep = reference_chain(confirmation_samples=8)
        self.assertEqual(
            shallow["first_request_entry_ms"], deep["first_request_entry_ms"]
        )
        self.assertEqual(deep["report_ms"] - shallow["report_ms"], 7 * 20.0)
        depth_timeout = reference_chain(confirmation_samples=8, deadline_ms=220.0)
        self.assertEqual(depth_timeout["status"], "deadline-missed")

        rejected = reference_chain(request_deg=70.0)
        broken = reference_chain(
            request_deg=70.0, architecture_mode="bypass-validation"
        )
        self.assertEqual(rejected["status"], "rejected")
        self.assertFalse(rejected["physical_motion"])
        self.assertEqual(broken["effective_target"], 45.0)
        self.assertEqual(broken["monitor_target"], 45.0)
        self.assertTrue(broken["reported_success"])
        self.assertTrue(broken["false_success"])
        self.assertFalse(broken["request_goal_met"])
        self.assertGreater(broken["request_error_at_report"], 25.0)
        self.assertLess(broken["monitor_error_at_report"], 0.5)
        self.assertEqual(broken["failure_mode"], "intent-lost")

    def test_independent_oracle_covers_deadline_cancellation_and_terminal_freeze(self):
        exact_deadline = reference_chain(deadline_ms=240.0)
        early_deadline = reference_chain(deadline_ms=220.0)
        self.assertTrue(exact_deadline["request_goal_met"])
        self.assertEqual(early_deadline["status"], "deadline-missed")

        cancel_zero = reference_chain(cancel_at_ms=0.0)
        cancel_mid = reference_chain(cancel_at_ms=120.0)
        cancel_tie = reference_chain(cancel_at_ms=240.0)
        cancel_after = reference_chain(cancel_at_ms=260.0)
        self.assertFalse(cancel_zero["physical_motion"])
        self.assertEqual(cancel_mid["status"], "cancelled")
        self.assertTrue(cancel_mid["physical_motion"])
        self.assertEqual(cancel_tie["status"], "cancelled")
        self.assertFalse(cancel_tie["reported_success"])
        self.assertEqual(cancel_after["status"], "completed")
        self.assertTrue(cancel_after["request_goal_met"])

        for result in (early_deadline, cancel_mid, exact_deadline):
            terminal = result["terminal_index"]
            self.assertTrue(
                all(
                    value == result["position_at_report"]
                    for value in result["positions"][terminal:]
                )
            )
            self.assertTrue(all(value == 0 for value in result["corrections"][terminal:]))

    def test_cancellation_deadline_tie_has_behavioral_coverage(self):
        cancel_deadline_tie = reference_chain(
            deadline_ms=100.0, cancel_at_ms=100.0
        )
        self.assertEqual(
            (
                cancel_deadline_tie["status"],
                cancel_deadline_tie["failure_mode"],
                cancel_deadline_tie["report_ms"],
                cancel_deadline_tie["cancel_observed_ms"],
                cancel_deadline_tie["reported_success"],
                cancel_deadline_tie["safe_hold"],
            ),
            ("cancelled", "cancelled", 100.0, 100.0, False, True),
        )

        checks = self.read("run_checks.m")
        self.assertIn(
            "cancelDeadlineTie = model(30,0.35,3,45,0.5,100,100,'complete');",
            checks,
        )
        self.assertIn(
            "Cancellation must have safety priority when tied with the deadline",
            checks,
        )

    def test_experiment_has_baselines_two_isolated_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sections), 2)
        self.assertIn("responseSweep = [0.20 0.35 0.50 0.70]", experiment)
        self.assertIn("confirmationSweep = [1 3 5 8]", experiment)
        self.assertIn("all(firstEntryByConfirmationMs ==", experiment)
        self.assertIn(
            "broken = model(70,0.35,3,45,0.5,1000,Inf,'bypass-validation')",
            experiment,
        )
        self.assertIn("Broken assumption", experiment)
        self.assertIn("~any(broken.functionActivation(:,2))", experiment)
        self.assertGreaterEqual(experiment.count("figure("), 5)
        self.assertGreaterEqual(experiment.count("xlabel("), 5)
        self.assertGreaterEqual(experiment.count("ylabel("), 5)
        for unit in ("(ms)", "(deg)", "(-)", "(samples)"):
            self.assertIn(unit, experiment)
        self.assertIn("Mechanism after lever 1", experiment)
        self.assertLess(
            experiment.index("Mechanism after lever 1"),
            experiment.index("%% Sweep 2"),
        )
        self.assertLess(
            experiment.index("Mechanism after lever 2"),
            experiment.index("%% Broken case"),
        )

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        for limits in (
            "'Limits',[-75 75]",
            "'Limits',[0 0.90]",
            "'Limits',[1 10]",
            "'Limits',[20 60]",
        ):
            self.assertIn(limits, interactive)
        self.assertGreaterEqual(interactive.count("uislider"), 3)
        self.assertGreaterEqual(interactive.count("uispinner"), 1)
        self.assertGreaterEqual(interactive.count("uidropdown"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangingFcn"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 7)
        self.assertIn("cancellation.ItemsData = [Inf 0 120 240]", interactive)
        self.assertIn("confirmation.RoundFractionalValues = 'on'", interactive)
        self.assertIn("deadlineValues = 100:20:2000", interactive)
        self.assertIn("deadline.ItemsData = deadlineValues", interactive)
        self.assertIn("'complete','bypass-validation'", interactive)
        self.assertIn("resetBaseline", interactive)
        self.assertIn("Original request, effective target, and observed state", interactive)
        self.assertIn("Function activation exposes omissions", interactive)
        self.assertIn("false success", interactive)
        self.assertIn("safe hold required", interactive)

    def test_checks_cover_failures_recovery_isolation_compatibility_and_bounds(self):
        checks = self.read("run_checks.m")
        self.assertGreaterEqual(checks.count("assert("), 35)
        for marker in (
            "expectedFirstEntryMs",
            "expectedPositionAtReportDeg",
            "slowResponse",
            "fastResponse",
            "unityResponse",
            "zeroResponse",
            "oneConfirmation",
            "eightConfirmations",
            "depthPastDeadline",
            "zeroRequest",
            "negativeRequest",
            "exactAuthority",
            "justOutsideAuthority",
            "rejectedRequest",
            "brokenIntent",
            "deadlineMiss",
            "deadlineTie",
            "oneUpdateEarly",
            "cancelBeforeMotion",
            "cancelDuringMotion",
            "cancelCompletionTie",
            "cancelDeadlineTie",
            "cancelAfterCompletion",
            "terminalSampleIndex",
            "safeHoldRequired",
            "maxBounded",
            "int16",
            "single",
            "uint8",
            "uint16",
            "string('complete')",
            "P04:InvalidTolerance",
            "P04:InvalidDeadlineGrid",
            "P04:InvalidCancelTime",
            "P04:InvalidArchitecture",
            "P04:ResourceBound",
            "afterFailure",
            "afterIsolationProbe",
            "isequaln(baseline,repeat)",
            "sampleCount == 151",
        ):
            self.assertIn(marker, checks)
        self.assertIn("P04 checks passed", checks)

    def test_lesson_is_concept_first_compounds_and_preserves_future_boundaries(self):
        combined = "\n".join(
            self.read(name)
            for name in (
                "README.md",
                "lesson.m",
                "lesson.md",
                "walkthrough.md",
                "checks.md",
            )
        )
        self.assertGreaterEqual(combined.count(QUESTION), 3)
        for marker in (
            "P03",
            "P05",
            "P06",
            "P07",
            "position[k+1]",
            "response_fraction",
            "position-plus-velocity",
            "input",
            "output",
            "failure",
            "cancellation",
            "deadline",
            "recovery",
            "teach-back",
            "interpretation",
        ):
            self.assertIn(marker.lower(), combined.lower())
        self.assertIn("not a replacement for P03", combined)
        self.assertIn("not a path-latency budget", combined)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_retained_evidence_exists_and_states_the_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P04-*.md"))
        self.assertTrue(evidence_files)
        evidence = "\n".join(
            path.read_text(encoding="utf-8") for path in evidence_files
        )
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
            "RT1/RT2",
            "Unreal",
            "signing",
            "deployment",
            "production",
        ):
            self.assertIn(marker, evidence)
        self.assertNotIn("Pending", evidence)
        self.assertRegex(evidence, r"\d+ tests passed")


if __name__ == "__main__":
    unittest.main()
