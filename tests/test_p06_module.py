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
P06 = ROOT / "modules/06-trace-a-command-path"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you trace a "
    "Command Path?"
)
STAGES = [
    "Capture intent",
    "Validate authority",
    "Compute error",
    "Generate correction",
    "Update physical state input latch",
]
OWNERS = [
    "application-software",
    "independent-hardware",
    "application-software",
    "application-software",
    "hardware-interface",
]
UNITS = ["deg", "deg", "deg", "deg/update", "deg/update"]
BOUNDARIES = [
    "request-to-authority",
    "authority-to-error",
    "error-to-correction",
    "correction-to-actuator",
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


def reference_trace(
    requested_angle: float = 30.0,
    observed_angle: float = 0.0,
    authority_limit: float = 45.0,
    response_fraction: float = 0.35,
    open_boundary: str = "none",
    event_mode: str = "none",
    assessment_mode: str = "endpoint-receipt",
) -> dict[str, object]:
    """Independent Python oracle for the documented P06 handoff contract."""
    stage_reached = [False] * len(STAGES)
    values = [math.nan] * len(STAGES)
    attempted = [False] * len(BOUNDARIES)
    crossed = [False] * len(BOUNDARIES)
    boundary_open = [open_boundary == name for name in BOUNDARIES]

    stage_reached[0] = True
    values[0] = requested_angle
    attempted[0] = True
    if not boundary_open[0]:
        crossed[0] = True
        stage_reached[1] = True
        values[1] = requested_angle

    authority_valid = abs(requested_angle) <= authority_limit
    authority_margin = authority_limit - abs(requested_angle)
    if stage_reached[1] and authority_valid:
        attempted[1] = True
        if not boundary_open[1]:
            crossed[1] = True
            stage_reached[2] = True

    accepted_target = (
        requested_angle if stage_reached[1] and authority_valid else math.nan
    )
    error = math.nan
    if stage_reached[2]:
        error = accepted_target - observed_angle
        values[2] = error
        attempted[2] = True
        if not boundary_open[2]:
            crossed[2] = True
            stage_reached[3] = True

    correction = math.nan
    local_dispatch = False
    event_guard_reached = False
    event_observed = False
    cancellation_observed = False
    timeout_observed = False
    tie_resolved_to_cancellation = False
    safe_hold_required = False
    safe_hold_available = False
    if stage_reached[3]:
        correction = response_fraction * error
        values[3] = correction
        local_dispatch = True
        event_guard_reached = True
        attempted[3] = True
        event_observed = event_mode != "none"
        cancellation_observed = event_mode in {
            "cancellation",
            "cancellation-timeout-tie",
        }
        timeout_observed = event_mode in {
            "timeout",
            "cancellation-timeout-tie",
        }
        tie_resolved_to_cancellation = event_mode == "cancellation-timeout-tie"
        if event_observed:
            safe_hold_required = True
            safe_hold_available = True
        elif not boundary_open[3]:
            crossed[3] = True
            stage_reached[4] = True
            values[4] = correction

    if stage_reached[1] and not authority_valid:
        safe_hold_required = True
        safe_hold_available = True

    endpoint_received = stage_reached[4]
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
    deepest = max(index + 1 for index, reached in enumerate(stage_reached) if reached)

    if endpoint_received:
        terminal = "delivered"
    elif stage_reached[1] and not authority_valid:
        terminal = "authority-rejected"
    elif cancellation_observed:
        terminal = "cancelled"
    elif timeout_observed:
        terminal = "timed-out"
    elif first_open:
        terminal = "boundary-open"
    else:
        terminal = "route-incomplete"

    handled = terminal in {
        "delivered",
        "authority-rejected",
        "cancelled",
        "timed-out",
    }
    if terminal == "authority-rejected":
        failure = "request-rejected"
    elif terminal == "cancelled":
        failure = "cancelled"
    elif terminal == "timed-out":
        failure = "timeout-observed"
    elif terminal == "boundary-open":
        failure = BOUNDARIES[first_open - 1]
    elif terminal == "route-incomplete":
        failure = "internal-route-incomplete"
    else:
        failure = "none"

    reported_success = (
        endpoint_received
        if assessment_mode == "endpoint-receipt"
        else local_dispatch
    )
    return {
        "stage_reached": stage_reached,
        "values": values,
        "attempted": attempted,
        "crossed": crossed,
        "boundary_open": boundary_open,
        "authority_valid": authority_valid,
        "authority_margin": authority_margin,
        "accepted_target": accepted_target,
        "error": error,
        "correction": correction,
        "local_dispatch": local_dispatch,
        "event_guard_reached": event_guard_reached,
        "event_observed": event_observed,
        "cancellation_observed": cancellation_observed,
        "timeout_observed": timeout_observed,
        "tie_resolved_to_cancellation": tie_resolved_to_cancellation,
        "safe_hold_required": safe_hold_required,
        "safe_hold_available": safe_hold_available,
        "endpoint_received": endpoint_received,
        "payload_preserved": endpoint_received and values[4] == values[3],
        "first_open": first_open,
        "deepest": deepest,
        "crossed_count": sum(crossed),
        "terminal": terminal,
        "handled": handled,
        "trace_contract_met": handled,
        "failure": failure,
        "reported_success": reported_success,
        "false_success": reported_success and not endpoint_received,
    }


def assert_oracle_invariants(test: unittest.TestCase, result: dict[str, object]) -> None:
    reached = result["stage_reached"]
    crossed = result["crossed"]
    attempted = result["attempted"]
    values = result["values"]
    test.assertEqual(reached[1:], crossed)
    test.assertTrue(all(not crossed[i] or attempted[i] for i in range(4)))
    test.assertEqual(reached, sorted(reached, reverse=True))
    test.assertTrue(all(math.isfinite(v) for v, active in zip(values, reached) if active))
    test.assertTrue(all(math.isnan(v) for v, active in zip(values, reached) if not active))
    test.assertEqual(result["deepest"], sum(reached))
    test.assertEqual(result["crossed_count"], sum(crossed))
    if result["endpoint_received"]:
        test.assertTrue(result["payload_preserved"])
        test.assertEqual(values[-1], result["correction"])


class P06ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P06")

    def read(self, name: str) -> str:
        return (P06 / name).read_text(encoding="utf-8")

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
                "number": 6,
                "id": "P06",
                "title": "Trace a Command Path",
                "guiding_question": QUESTION,
                "phase": 2,
                "phase_title": "Allocation and interfaces",
                "slug": "trace-a-command-path",
                "folder": "modules/06-trace-a-command-path",
                "implementation_batch": "P06",
                "prerequisites": ["P05"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P05"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P06.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_residue_and_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            with self.subTest(path=name):
                content = self.read(name)
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                lowered = content.lower()
                for residue in ("scaffolded", "activate its governed", "todo"):
                    self.assertNotIn(residue, lowered)

    def test_model_is_transparent_presentation_free_and_resource_bounded(self):
        model = self.read("model.m")
        compact = re.sub(r"\s+|\.\.\.", "", model)
        self.assertIn("function out = model(", model)
        self.assertIn("maxAbsAngleDeg = 180", model)
        self.assertIn("errorDeg=acceptedTargetDeg-observedAngleDeg;", compact)
        self.assertIn("correctionDegPerUpdate=responseFraction*errorDeg;", compact)
        self.assertIn("stageReached(2:end)", self.read("run_checks.m"))
        self.assertIn("abs(requestedAngleDeg)<=authorityLimitDeg", compact)
        self.assertIn("stageReached(5)=true;", compact)
        self.assertIn("stageOutputValue(5)=correctionDegPerUpdate;", compact)
        self.assertIn("tieResolvedToCancellation", model)
        self.assertIn("reportedSuccess=actuatorCommandReceived;", compact)
        self.assertIn("reportedSuccess=localDispatchObserved;", compact)
        self.assertIn("falseSuccess=reportedSuccess&&~actuatorCommandReceived;", compact)
        self.assertIn("P06:InvalidAngle", model)
        self.assertIn("P06:InvalidAuthority", model)
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

    def test_independent_oracle_baseline_and_limiting_equations(self):
        baseline = reference_trace()
        assert_oracle_invariants(self, baseline)
        self.assertEqual(baseline["values"], [30.0, 30.0, 30.0, 10.5, 10.5])
        self.assertEqual(baseline["authority_margin"], 15.0)
        self.assertTrue(baseline["endpoint_received"])
        self.assertTrue(baseline["trace_contract_met"])
        self.assertEqual(baseline["terminal"], "delivered")
        self.assertFalse(baseline["false_success"])

        exact = reference_trace(authority_limit=30)
        below = reference_trace(authority_limit=29.999)
        negative = reference_trace(requested_angle=-30, authority_limit=30)
        zero_error = reference_trace(observed_angle=30)
        zero_response = reference_trace(response_fraction=0)
        full_response = reference_trace(response_fraction=1)
        maximum = reference_trace(
            requested_angle=180,
            observed_angle=-180,
            authority_limit=180,
            response_fraction=1,
        )
        for result in (exact, below, negative, zero_error, zero_response, full_response, maximum):
            assert_oracle_invariants(self, result)
        self.assertTrue(exact["endpoint_received"])
        self.assertEqual(exact["authority_margin"], 0)
        self.assertEqual(below["deepest"], 2)
        self.assertEqual(below["terminal"], "authority-rejected")
        self.assertTrue(below["safe_hold_required"])
        self.assertTrue(below["trace_contract_met"])
        self.assertFalse(below["endpoint_received"])
        self.assertEqual(negative["correction"], -10.5)
        self.assertEqual(zero_error["correction"], 0)
        self.assertEqual(zero_response["correction"], 0)
        self.assertEqual(full_response["correction"], 30)
        self.assertEqual(maximum["correction"], 360)

    def test_independent_oracle_all_boundaries_and_isolation(self):
        expected_depth = {
            "request-to-authority": 1,
            "authority-to-error": 2,
            "error-to-correction": 3,
            "correction-to-actuator": 4,
        }
        for boundary, depth in expected_depth.items():
            with self.subTest(boundary=boundary):
                result = reference_trace(open_boundary=boundary)
                assert_oracle_invariants(self, result)
                self.assertEqual(result["first_open"], depth)
                self.assertEqual(result["deepest"], depth)
                self.assertEqual(result["crossed_count"], depth - 1)
                self.assertEqual(result["terminal"], "boundary-open")
                self.assertEqual(result["failure"], boundary)
                self.assertFalse(result["trace_contract_met"])
                self.assertFalse(result["endpoint_received"])

        earlier_stop = reference_trace(
            open_boundary="error-to-correction", event_mode="cancellation"
        )
        self.assertFalse(earlier_stop["event_guard_reached"])
        self.assertFalse(earlier_stop["event_observed"])
        self.assertFalse(earlier_stop["safe_hold_required"])
        self.assertEqual(earlier_stop["terminal"], "boundary-open")

        validation_first = reference_trace(
            requested_angle=60, authority_limit=45, event_mode="cancellation"
        )
        self.assertEqual(validation_first["terminal"], "authority-rejected")
        self.assertFalse(validation_first["cancellation_observed"])
        self.assertTrue(validation_first["safe_hold_required"])

    def test_independent_oracle_cancellation_timeout_tie_and_broken_report(self):
        cancelled = reference_trace(event_mode="cancellation")
        timed_out = reference_trace(event_mode="timeout")
        tied = reference_trace(event_mode="cancellation-timeout-tie")
        for result in (cancelled, timed_out, tied):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["event_guard_reached"])
            self.assertTrue(result["event_observed"])
            self.assertTrue(result["safe_hold_required"])
            self.assertTrue(result["safe_hold_available"])
            self.assertFalse(result["endpoint_received"])
            self.assertTrue(result["trace_contract_met"])
        self.assertEqual(cancelled["terminal"], "cancelled")
        self.assertEqual(cancelled["failure"], "cancelled")
        self.assertEqual(timed_out["terminal"], "timed-out")
        self.assertEqual(timed_out["failure"], "timeout-observed")
        self.assertTrue(tied["cancellation_observed"])
        self.assertTrue(tied["timeout_observed"])
        self.assertTrue(tied["tie_resolved_to_cancellation"])
        self.assertEqual(tied["terminal"], "cancelled")

        complete = reference_trace(open_boundary="correction-to-actuator")
        broken = reference_trace(
            open_boundary="correction-to-actuator", assessment_mode="dispatch-only"
        )
        for factual_key in (
            "stage_reached",
            "attempted",
            "crossed",
            "boundary_open",
            "terminal",
            "failure",
        ):
            self.assertEqual(complete[factual_key], broken[factual_key])
        for complete_value, broken_value in zip(complete["values"], broken["values"]):
            if math.isnan(complete_value):
                self.assertTrue(math.isnan(broken_value))
            else:
                self.assertEqual(complete_value, broken_value)
        self.assertTrue(broken["local_dispatch"])
        self.assertFalse(broken["endpoint_received"])
        self.assertFalse(complete["reported_success"])
        self.assertTrue(broken["reported_success"])
        self.assertTrue(broken["false_success"])

    def test_final_guard_precedes_open_final_handoff_behaviorally(self):
        event_before_open = reference_trace(
            open_boundary="correction-to-actuator", event_mode="timeout"
        )
        assert_oracle_invariants(self, event_before_open)
        self.assertTrue(event_before_open["event_guard_reached"])
        self.assertTrue(event_before_open["event_observed"])
        self.assertTrue(event_before_open["timeout_observed"])
        self.assertTrue(event_before_open["attempted"][3])
        self.assertTrue(event_before_open["boundary_open"][3])
        self.assertFalse(event_before_open["crossed"][3])
        self.assertEqual(event_before_open["first_open"], 4)
        self.assertFalse(event_before_open["endpoint_received"])
        self.assertTrue(event_before_open["safe_hold_required"])
        self.assertTrue(event_before_open["safe_hold_available"])
        self.assertTrue(event_before_open["handled"])
        self.assertTrue(event_before_open["trace_contract_met"])
        self.assertEqual(event_before_open["terminal"], "timed-out")
        self.assertEqual(event_before_open["failure"], "timeout-observed")
        self.assertFalse(event_before_open["reported_success"])
        self.assertFalse(event_before_open["false_success"])

        checks = self.read("run_checks.m")
        self.assertIn(
            "eventBeforeOpenFinal = model(30,0,45,0.35,'correction-to-actuator',",
            checks,
        )
        self.assertIn(
            "A reached event guard must determine the terminal before an open final handoff.",
            checks,
        )

    def test_every_supported_terminal_is_behaviorally_reachable(self):
        scenarios = [
            reference_trace(),
            reference_trace(requested_angle=60, authority_limit=45),
            reference_trace(event_mode="cancellation"),
            reference_trace(event_mode="timeout"),
            reference_trace(open_boundary="request-to-authority"),
        ]
        self.assertEqual(
            {scenario["terminal"] for scenario in scenarios},
            {
                "delivered",
                "authority-rejected",
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
            "authoritySweepDeg = [20 30 45 90]",
            "boundarySweep = {'none','request-to-authority'",
            "isequal(deepestStageByAuthority,[2 5 5 5])",
            "isequal(deepestStageByBoundary,[5 1 2 3 4])",
            "cancellation-timeout-tie",
            "dispatch-only",
            "broken.falseSuccess",
            "isequaln(recovered,baseline)",
        ):
            self.assertIn(marker, experiment)
        self.assertLess(
            experiment.index("Mechanism after lever 1"), experiment.index("%% Sweep 2")
        )
        self.assertLess(
            experiment.index("Mechanism after lever 2"), experiment.index("%% Broken case")
        )
        for unit in ("(deg)", "(deg/update)", "Boolean -", "stage (-)"):
            self.assertIn(unit, experiment)
        self.assertIn("P07 owns measurement data", experiment)
        self.assertIn("P08 owns interface contracts", experiment)
        self.assertIn("P11 owns timing and jitter", experiment)

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertGreaterEqual(interactive.count("uispinner"), 4)
        self.assertGreaterEqual(interactive.count("uidropdown"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 7)
        self.assertIn("'Limits',[-180 180]", interactive)
        self.assertIn("'Limits',[1 180]", interactive)
        self.assertIn("'Limits',[0 1]", interactive)
        self.assertIn("openBoundary.ItemsData", interactive)
        self.assertIn("cancellation-timeout-tie", interactive)
        self.assertIn("assessmentMode.ItemsData = {'endpoint-receipt','dispatch-only'}", interactive)
        self.assertIn("resetBaseline", interactive)
        for marker in (
            "requestedAngle.Value = 30",
            "observedAngle.Value = 0",
            "authorityLimit.Value = 45",
            "responseFraction.Value = 0.35",
            "openBoundary.Value = 'none'",
            "eventMode.Value = 'none'",
            "assessmentMode.Value = 'endpoint-receipt'",
        ):
            self.assertIn(marker, interactive)
        self.assertIn("Stage reached (Boolean -)", interactive)
        self.assertIn("Boundary disposition (Boolean -)", interactive)
        self.assertIn("actuator input receipt", interactive)
        self.assertIn("false success", interactive)

    def test_checks_cover_failures_recovery_compatibility_and_bounds(self):
        checks = self.read("run_checks.m")
        for marker in (
            "expectedStageNames",
            "expectedStageOwners",
            "expectedStageUnits",
            "expectedBoundaryNames",
            "authorityBelow",
            "authorityExact",
            "negativeExact",
            "zeroError",
            "zeroResponse",
            "fullResponse",
            "maxEnvelope",
            "boundaryChoices",
            "cancelled",
            "timedOut",
            "tied",
            "unreachedGuard",
            "validationFirst",
            "eventBeforeOpenFinal",
            "brokenDispatchOnly",
            "string(' NONE ')",
            "P06:InvalidAngle",
            "P06:InvalidAuthority",
            "P06:InvalidResponseFraction",
            "P06:InvalidBoundary",
            "P06:InvalidEventMode",
            "P06:InvalidAssessmentMode",
            "afterMalformed",
            "assertTraceInvariant",
            "P06 checks passed",
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
            "P07",
            "P08",
            "P11",
            "input",
            "observable",
            "failure",
            "authority",
            "boundary",
            "cancellation",
            "timeout",
            "recovery",
            "interpretation",
            "teach-back",
            "deg/update",
        ):
            self.assertIn(marker.lower(), combined.lower())
        self.assertIn("not evidence of electrical signaling", combined)
        self.assertIn("not physical motion", combined)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_rollback_fixture_recovers_persisted_p06_to_p05(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 6:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            (state_dir / "progress.json").write_text(
                json.dumps({"current": "P06", "completed": {}, "notes": {}}) + "\n",
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
            self.assertIn(
                "P05 — Allocate Functions Across Hardware and Software", recovered.stdout
            )
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P05")

    def test_retained_evidence_has_required_sections_and_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P06-*.md"))
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
