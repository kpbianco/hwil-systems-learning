from __future__ import annotations

import copy
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
P11 = ROOT / "modules/11-budget-latency-and-jitter"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you budget "
    "Latency and Jitter?"
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
PATTERN = [
    [0, 0, 0, 0],
    [1, -1, 0, 1],
    [-1, 1, 1, 0],
    [1, 1, 1, 1],
    [0, -1, -1, 1],
    [-1, 0, 1, -1],
    [1, 0, -1, 0],
    [-1, -1, -1, -1],
    [0, 1, 0, -1],
    [1, -1, 1, -1],
    [-1, 1, -1, 1],
    [0, 0, 0, 0],
]


def _number(value: object, lower: float, upper: float, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not lower <= float(value) <= upper
    ):
        raise ValueError(name)
    return float(value)


def _logical(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value in (0, 1)
    ):
        return bool(value)
    raise ValueError("p10_activation_proof")


def _cancellation(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or math.isnan(float(value))
        or float(value) < 0
        or (math.isinf(float(value)) and float(value) < 0)
    ):
        raise ValueError("cancel_at_ms")
    return float(value)


def _choice(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("assessment_mode")
    normalized = value.strip().lower()
    if normalized not in {"bounded-sum", "rss-uncorrelated"}:
        raise ValueError("assessment_mode")
    return normalized


def reference_budget(
    transport_nominal_ms: float = 1.2,
    jitter_scale: float = 1.0,
    deadline_ms: float = 4.2,
    p10_activation_proof: bool = True,
    cancel_at_ms: float = math.inf,
    assessment_mode: str = "bounded-sum",
) -> dict[str, object]:
    """Independent Python oracle for P11's deterministic timing contract."""
    transport_nominal_ms = _number(
        transport_nominal_ms, 0.6, 2.4, "transport_nominal_ms"
    )
    jitter_scale = _number(jitter_scale, 0.0, 2.0, "jitter_scale")
    deadline_ms = _number(deadline_ms, 0.5, 10.0, "deadline_ms")
    p10_activation_proof = _logical(p10_activation_proof)
    cancel_at_ms = _cancellation(cancel_at_ms)
    assessment_mode = _choice(assessment_mode)

    cycle_count = 12
    stage_count = 4
    period_ms = 6.0
    nominal_stage_ms = [0.6, 0.5, transport_nominal_ms, 1.0]
    base_allocations_ms = [0.1, 0.1, 0.3, 0.2]
    allocations_ms = [jitter_scale * value for value in base_allocations_ms]
    planned_stage_ms = [
        [
            nominal_stage_ms[column] + allocations_ms[column] * row[column]
            for column in range(stage_count)
        ]
        for row in PATTERN
    ]
    planned_latency_ms = [sum(row) for row in planned_stage_ms]
    nominal_latency_ms = sum(nominal_stage_ms)
    strict_jitter_ms = sum(allocations_ms)
    strict_lower_ms = nominal_latency_ms - strict_jitter_ms
    strict_upper_ms = nominal_latency_ms + strict_jitter_ms
    rss_jitter_ms = math.sqrt(sum(value * value for value in allocations_ms))
    rss_upper_ms = nominal_latency_ms + rss_jitter_ms
    reported_upper_ms = (
        strict_upper_ms if assessment_mode == "bounded-sum" else rss_upper_ms
    )
    strict_pass = strict_upper_ms <= deadline_ms
    reported_pass = reported_upper_ms <= deadline_ms
    strict_accepted = p10_activation_proof and strict_pass
    reported_accepted = p10_activation_proof and reported_pass

    releases_ms = [index * period_ms for index in range(cycle_count)]
    deadlines_ms = [value + deadline_ms for value in releases_ms]
    completions_ms = [
        releases_ms[index] + planned_latency_ms[index]
        for index in range(cycle_count)
    ]
    planned_miss = [
        completions_ms[index] > deadlines_ms[index]
        for index in range(cycle_count)
    ]

    started = [False] * cycle_count
    completed = [False] * cycle_count
    actual_releases_ms = [math.nan] * cycle_count
    actual_completions_ms = [math.nan] * cycle_count
    actual_latency_ms = [math.nan] * cycle_count
    cancellation_observed = False
    timeout_observed = False
    tie_to_cancellation = False
    terminal_time_ms = math.nan
    interrupted_cycle = math.nan

    if p10_activation_proof:
        for index in range(cycle_count):
            release_ms = releases_ms[index]
            completion_ms = completions_ms[index]
            absolute_deadline_ms = deadlines_ms[index]
            if cancel_at_ms <= release_ms:
                cancellation_observed = True
                terminal_time_ms = cancel_at_ms
                interrupted_cycle = index + 1
                break

            started[index] = True
            actual_releases_ms[index] = release_ms
            timeout_candidate_ms = (
                absolute_deadline_ms if completion_ms > absolute_deadline_ms else math.inf
            )
            if (
                cancel_at_ms <= completion_ms
                and cancel_at_ms <= timeout_candidate_ms
            ):
                cancellation_observed = True
                timeout_observed = math.isfinite(timeout_candidate_ms) and math.isclose(
                    cancel_at_ms,
                    timeout_candidate_ms,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                tie_to_cancellation = timeout_observed
                terminal_time_ms = cancel_at_ms
                interrupted_cycle = index + 1
                break
            if timeout_candidate_ms < completion_ms and timeout_candidate_ms < cancel_at_ms:
                timeout_observed = True
                terminal_time_ms = timeout_candidate_ms
                interrupted_cycle = index + 1
                break

            completed[index] = True
            actual_completions_ms[index] = completion_ms
            actual_latency_ms[index] = planned_latency_ms[index]

    schedule_completed = all(completed)
    event_observed = cancellation_observed or timeout_observed
    if not p10_activation_proof:
        terminal = "blocked-p10-activation-proof"
        failure = "p10-activation-proof-unavailable"
    elif cancellation_observed and timeout_observed:
        terminal = "cancelled-on-timeout-tie"
        failure = "cycle-cancelled"
    elif cancellation_observed:
        terminal = "cancelled-safe-hold-requested"
        failure = "cycle-cancelled"
    elif timeout_observed:
        terminal = "timed-out-safe-hold-requested"
        failure = "deadline-timeout"
    elif schedule_completed:
        terminal = "completed-within-budget"
        failure = "none"
    else:
        terminal = "unhandled-terminal"
        failure = "unhandled-terminal"

    false_approval = reported_accepted and not strict_accepted
    return {
        "nominal_stage_ms": nominal_stage_ms,
        "allocations_ms": allocations_ms,
        "planned_stage_ms": planned_stage_ms,
        "planned_latency_ms": planned_latency_ms,
        "nominal_latency_ms": nominal_latency_ms,
        "strict_jitter_ms": strict_jitter_ms,
        "strict_lower_ms": strict_lower_ms,
        "strict_upper_ms": strict_upper_ms,
        "strict_peak_to_peak_ms": 2 * strict_jitter_ms,
        "rss_jitter_ms": rss_jitter_ms,
        "rss_upper_ms": rss_upper_ms,
        "reported_upper_ms": reported_upper_ms,
        "strict_margin_ms": deadline_ms - strict_upper_ms,
        "reported_margin_ms": deadline_ms - reported_upper_ms,
        "strict_pass": strict_pass,
        "reported_pass": reported_pass,
        "strict_accepted": strict_accepted,
        "reported_accepted": reported_accepted,
        "false_approval": false_approval,
        "assessment_correct": strict_accepted == reported_accepted,
        "releases_ms": releases_ms,
        "deadlines_ms": deadlines_ms,
        "completions_ms": completions_ms,
        "planned_miss": planned_miss,
        "started": started,
        "completed": completed,
        "actual_releases_ms": actual_releases_ms,
        "actual_completions_ms": actual_completions_ms,
        "actual_latency_ms": actual_latency_ms,
        "schedule_completed": schedule_completed,
        "cancellation_requested": math.isfinite(cancel_at_ms),
        "cancellation_observed": cancellation_observed,
        "timeout_observed": timeout_observed,
        "tie_to_cancellation": tie_to_cancellation,
        "terminal_time_ms": terminal_time_ms,
        "interrupted_cycle": interrupted_cycle,
        "safe_hold_requested": event_observed,
        "rollback_required": event_observed,
        "rollback_evidence_available": False,
        "rollback_authority": "P10",
        "terminal": terminal,
        "failure": failure,
        "reporting_failure": (
            "rss-independence-false-approval" if false_approval else "none"
        ),
        "cycle_count": cycle_count,
        "stage_count": stage_count,
        "stage_cell_count": cycle_count * stage_count,
    }


def assert_nan_suffix(test: unittest.TestCase, values: list[float], start: int) -> None:
    test.assertTrue(all(math.isnan(value) for value in values[start:]))


def assert_close_sequence(
    test: unittest.TestCase,
    actual: list[float],
    expected: list[float],
    tolerance: float = 1e-12,
) -> None:
    test.assertEqual(len(actual), len(expected))
    test.assertTrue(
        all(
            math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)
            for left, right in zip(actual, expected)
        ),
        f"sequences differ: {actual!r} != {expected!r}",
    )


class P11ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P11")

    def read(self, name: str) -> str:
        path = P11 / name
        self.assertTrue(path.is_file(), f"missing required P11 artifact: {path}")
        return path.read_text(encoding="utf-8")

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
                "number": 11,
                "id": "P11",
                "title": "Budget Latency and Jitter",
                "guiding_question": QUESTION,
                "phase": 3,
                "phase_title": "Sequencing and synchronization",
                "slug": "budget-latency-and-jitter",
                "folder": "modules/11-budget-latency-and-jitter",
                "implementation_batch": "P11",
                "prerequisites": ["P10"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P10"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P11.iterdir() if path.is_file()}
        )

    def test_owned_text_has_no_residue_and_exact_terminal_newline(self):
        owned_paths = [P11 / name for name in sorted(REQUIRED_ARTIFACTS)]
        owned_paths.append(Path(__file__))
        owned_paths.extend(sorted((ROOT / "docs/evidence").glob("P11-*.md")))
        for path in owned_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file(), f"missing owned text file: {path}")
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                if path.parent == P11:
                    lowered = content.lower()
                    for residue in (
                        "status: scaffolded",
                        "activate its governed",
                        "todo",
                        "placeholder",
                    ):
                        self.assertNotIn(residue, lowered)

    def test_model_is_transparent_presentation_free_and_resource_bounded(self):
        model = self.read("model.m")
        compact = re.sub(r"\s+|\.\.\.", "", model)
        self.assertRegex(
            model,
            r"function out = model\(transportNominalMs,jitterScale,deadlineMs,\s*\.\.\.\s*p10ActivationProof,cancelAtMs,assessmentMode\)",
        )
        for marker in (
            "minimumTransportNominalMs = 0.6",
            "maximumTransportNominalMs = 2.4",
            "minimumJitterScale = 0.0",
            "maximumJitterScale = 2.0",
            "minimumDeadlineMs = 0.5",
            "maximumDeadlineMs = 10.0",
            "cycleCount = 12",
            "stageCount = 4",
            "stageCellCount = cycleCount * stageCount",
            "cyclePeriodMs = 6.0",
            "baseJitterAllocationMs = [0.1 0.1 0.3 0.2]",
            "jitterPattern",
            "plannedStageLatencyMs",
            "plannedLatencyMs",
            "actualLatencyMs",
            "cycleStarted",
            "cycleCompleted",
            "safeHoldRequested",
            "rollbackEvidenceAvailable",
            "rollbackAuthority",
        ):
            self.assertIn(marker, model)
        for formula in (
            "plannedStageVariationMs=jitterPattern.*jitterAllocationMs;",
            "plannedStageLatencyMs=nominalStageLatencyMs+plannedStageVariationMs;",
            "plannedLatencyMs=sum(plannedStageLatencyMs,2)';",
            "strictJitterAllowanceMs=sum(jitterAllocationMs);",
            "strictUpperBoundMs=nominalLatencyMs+strictJitterAllowanceMs;",
            "rssJitterAllowanceMs=sqrt(sum(jitterAllocationMs.^2));",
            "plannedReleaseMs=(cycleIndex-1).*cyclePeriodMs;",
            "plannedDeadlineMs=plannedReleaseMs+deadlineMs;",
            "plannedCompletionMs=plannedReleaseMs+plannedLatencyMs;",
            "strictBudgetPass=strictUpperBoundMs<=deadlineMs;",
            "reportedBudgetPass=reportedUpperBoundMs<=deadlineMs;",
            "falseApproval=reportedBudgetAccepted&&~strictBudgetAccepted;",
            "rollbackEvidenceAvailable=false;",
            "rollbackAuthority='P10';",
        ):
            self.assertIn(formula, compact)
        for error_id in (
            "P11:InvalidTransportNominal",
            "P11:InvalidJitterScale",
            "P11:InvalidDeadline",
            "P11:InvalidP10ActivationProof",
            "P11:InvalidCancellationTime",
            "P11:InvalidAssessmentMode",
            "blocked-p10-activation-proof",
            "cancelled-safe-hold-requested",
            "timed-out-safe-hold-requested",
            "cancelled-on-timeout-tie",
            "rss-independence-false-approval",
        ):
            self.assertIn(error_id, model)

        lowered = model.lower()
        for forbidden in (
            "figure(",
            "plot(",
            "uifigure(",
            "rng(",
            "rand(",
            "randn(",
            "timer(",
            "pause(",
            "persistent ",
            "global ",
            "fopen(",
            "webread(",
            "serialport(",
            "tcpclient(",
            "udpport(",
            "eval(",
            "sim(",
            "system(",
            "intlinprog(",
            "fmincon(",
            "prctile(",
            "norminv(",
        ):
            self.assertNotIn(forbidden, lowered)

        all_matlab = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(P11.glob("*.m"))
        ).lower()
        for opaque_or_external in (
            "rng(",
            "rand(",
            "randn(",
            "timer(",
            "sim(",
            "fmincon(",
            "intlinprog(",
            "webread(",
            "serialport(",
            "tcpclient(",
            "udpport(",
        ):
            self.assertNotIn(opaque_or_external, all_matlab)

    def test_independent_oracle_baseline_exact_trace_and_metrics(self):
        baseline = reference_budget()
        assert_close_sequence(
            self,
            baseline["planned_latency_ms"],
            [3.3, 3.5, 3.6, 4.0, 3.1, 3.3, 3.1, 2.6, 3.2, 3.4, 3.2, 3.3],
        )
        self.assertTrue(
            all(sum(row[column] for row in PATTERN) == 0 for column in range(4))
        )
        self.assertEqual(PATTERN[3], [1, 1, 1, 1])
        self.assertEqual(PATTERN[7], [-1, -1, -1, -1])
        self.assertAlmostEqual(baseline["nominal_latency_ms"], 3.3)
        self.assertAlmostEqual(baseline["strict_jitter_ms"], 0.7)
        self.assertAlmostEqual(baseline["strict_lower_ms"], 2.6)
        self.assertAlmostEqual(baseline["strict_upper_ms"], 4.0)
        self.assertAlmostEqual(baseline["strict_margin_ms"], 0.2)
        self.assertAlmostEqual(baseline["strict_peak_to_peak_ms"], 1.4)
        self.assertAlmostEqual(
            max(baseline["planned_latency_ms"]) - min(baseline["planned_latency_ms"]),
            1.4,
        )
        self.assertAlmostEqual(
            sum(baseline["planned_latency_ms"]) / baseline["cycle_count"], 3.3
        )
        self.assertEqual(baseline["releases_ms"], list(range(0, 72, 6)))
        self.assertEqual(baseline["deadlines_ms"], [4.2 + 6 * i for i in range(12)])
        self.assertFalse(any(baseline["planned_miss"]))
        self.assertTrue(all(baseline["started"]))
        self.assertTrue(all(baseline["completed"]))
        self.assertEqual(baseline["actual_releases_ms"], baseline["releases_ms"])
        self.assertEqual(baseline["actual_completions_ms"], baseline["completions_ms"])
        self.assertEqual(baseline["actual_latency_ms"], baseline["planned_latency_ms"])
        self.assertTrue(baseline["schedule_completed"])
        self.assertTrue(baseline["strict_accepted"])
        self.assertTrue(baseline["reported_accepted"])
        self.assertEqual(baseline["terminal"], "completed-within-budget")
        self.assertEqual(baseline["stage_cell_count"], 48)

    def test_independent_oracle_transport_sweep_and_limits(self):
        sweep = [0.6, 1.2, 1.8, 2.4]
        results = [reference_budget(transport_nominal_ms=value) for value in sweep]
        self.assertEqual(
            [round(result["strict_upper_ms"], 12) for result in results],
            [3.4, 4.0, 4.6, 5.2],
        )
        self.assertEqual(
            [round(result["strict_margin_ms"], 12) for result in results],
            [0.8, 0.2, -0.4, -1.0],
        )
        self.assertTrue(
            all(math.isclose(result["strict_peak_to_peak_ms"], 1.4) for result in results)
        )
        with self.assertRaises(ValueError):
            reference_budget(transport_nominal_ms=0.599)
        with self.assertRaises(ValueError):
            reference_budget(transport_nominal_ms=2.401)

    def test_independent_oracle_jitter_sweep_and_deadline_limits(self):
        sweep = [0, 0.5, 1, 1.5, 2]
        results = [reference_budget(jitter_scale=value) for value in sweep]
        expected_upper = [3.3, 3.65, 4.0, 4.35, 4.7]
        expected_margin = [0.9, 0.55, 0.2, -0.15, -0.5]
        expected_peak_to_peak = [0, 0.7, 1.4, 2.1, 2.8]
        for result, upper, margin, peak_to_peak in zip(
            results, expected_upper, expected_margin, expected_peak_to_peak
        ):
            self.assertAlmostEqual(result["strict_upper_ms"], upper)
            self.assertAlmostEqual(result["strict_margin_ms"], margin)
            self.assertAlmostEqual(result["strict_peak_to_peak_ms"], peak_to_peak)
            self.assertAlmostEqual(result["nominal_latency_ms"], 3.3)

        zero = reference_budget(jitter_scale=0, deadline_ms=3.3)
        exact = reference_budget(deadline_ms=4.0)
        self.assertEqual(zero["planned_latency_ms"], [3.3] * 12)
        self.assertTrue(zero["schedule_completed"])
        self.assertTrue(zero["strict_accepted"])
        self.assertTrue(exact["schedule_completed"])
        self.assertTrue(exact["strict_accepted"])
        self.assertFalse(exact["timeout_observed"])
        with self.assertRaises(ValueError):
            reference_budget(jitter_scale=-0.001)
        with self.assertRaises(ValueError):
            reference_budget(jitter_scale=2.001)

    def test_broken_rss_false_approval_preserves_factual_trace(self):
        strict = reference_budget(jitter_scale=2, assessment_mode="bounded-sum")
        broken = reference_budget(jitter_scale=2, assessment_mode="rss-uncorrelated")
        assert_close_sequence(
            self,
            broken["planned_latency_ms"],
            [3.3, 3.7, 3.9, 4.7, 2.9, 3.3, 2.9, 1.9, 3.1, 3.5, 3.1, 3.3],
        )
        self.assertEqual(strict["planned_stage_ms"], broken["planned_stage_ms"])
        self.assertEqual(strict["planned_latency_ms"], broken["planned_latency_ms"])
        self.assertEqual(strict["started"], broken["started"])
        self.assertEqual(strict["completed"], broken["completed"])
        self.assertAlmostEqual(broken["strict_upper_ms"], 4.7)
        self.assertAlmostEqual(broken["rss_jitter_ms"], math.sqrt(0.6))
        self.assertAlmostEqual(broken["reported_upper_ms"], 3.3 + math.sqrt(0.6))
        self.assertFalse(broken["strict_pass"])
        self.assertTrue(broken["reported_pass"])
        self.assertFalse(broken["strict_accepted"])
        self.assertTrue(broken["reported_accepted"])
        self.assertTrue(broken["false_approval"])
        self.assertFalse(broken["assessment_correct"])
        self.assertTrue(broken["timeout_observed"])
        self.assertEqual(broken["interrupted_cycle"], 4)
        self.assertEqual(
            broken["reporting_failure"], "rss-independence-false-approval"
        )

    def test_cancellation_masks_unfinished_actual_evidence_and_requests_handoff(self):
        cancelled = reference_budget(cancel_at_ms=15)
        self.assertEqual(cancelled["started"], [True, True, True] + [False] * 9)
        self.assertEqual(cancelled["completed"], [True, True] + [False] * 10)
        self.assertEqual(cancelled["actual_latency_ms"][:2], [3.3, 3.5])
        self.assertEqual(
            cancelled["actual_completions_ms"][:2],
            cancelled["completions_ms"][:2],
        )
        assert_nan_suffix(self, cancelled["actual_latency_ms"], 2)
        assert_nan_suffix(self, cancelled["actual_completions_ms"], 2)
        self.assertTrue(cancelled["cancellation_requested"])
        self.assertTrue(cancelled["cancellation_observed"])
        self.assertFalse(cancelled["timeout_observed"])
        self.assertEqual(cancelled["interrupted_cycle"], 3)
        self.assertEqual(cancelled["terminal_time_ms"], 15)
        self.assertTrue(cancelled["safe_hold_requested"])
        self.assertTrue(cancelled["rollback_required"])
        self.assertFalse(cancelled["rollback_evidence_available"])
        self.assertEqual(cancelled["rollback_authority"], "P10")
        self.assertEqual(cancelled["terminal"], "cancelled-safe-hold-requested")
        self.assertTrue(all(math.isfinite(value) for value in cancelled["planned_latency_ms"]))

        before_start = reference_budget(cancel_at_ms=0)
        self.assertFalse(any(before_start["started"]))
        self.assertEqual(before_start["interrupted_cycle"], 1)
        completion_tied = reference_budget(cancel_at_ms=9.5)
        self.assertEqual(completion_tied["started"], [True, True] + [False] * 10)
        self.assertEqual(completion_tied["completed"], [True] + [False] * 11)
        self.assertTrue(completion_tied["cancellation_observed"])
        self.assertFalse(completion_tied["timeout_observed"])
        self.assertEqual(completion_tied["interrupted_cycle"], 2)
        self.assertEqual(completion_tied["terminal_time_ms"], 9.5)
        assert_nan_suffix(self, completion_tied["actual_latency_ms"], 1)
        after_schedule = reference_budget(cancel_at_ms=100)
        self.assertTrue(after_schedule["schedule_completed"])
        self.assertFalse(after_schedule["cancellation_observed"])

    def test_timeout_is_derived_and_cancellation_wins_exact_tie(self):
        timed_out = reference_budget(jitter_scale=2)
        self.assertEqual(timed_out["started"], [True] * 4 + [False] * 8)
        self.assertEqual(timed_out["completed"], [True] * 3 + [False] * 9)
        assert_close_sequence(self, timed_out["actual_latency_ms"][:3], [3.3, 3.7, 3.9])
        assert_nan_suffix(self, timed_out["actual_latency_ms"], 3)
        self.assertFalse(timed_out["cancellation_observed"])
        self.assertTrue(timed_out["timeout_observed"])
        self.assertEqual(timed_out["interrupted_cycle"], 4)
        self.assertAlmostEqual(timed_out["terminal_time_ms"], 22.2)
        self.assertEqual(timed_out["failure"], "deadline-timeout")
        self.assertEqual(timed_out["terminal"], "timed-out-safe-hold-requested")

        tied = reference_budget(jitter_scale=2, cancel_at_ms=22.2)
        self.assertTrue(tied["cancellation_observed"])
        self.assertTrue(tied["timeout_observed"])
        self.assertTrue(tied["tie_to_cancellation"])
        self.assertEqual(tied["interrupted_cycle"], 4)
        self.assertEqual(tied["failure"], "cycle-cancelled")
        self.assertEqual(tied["terminal"], "cancelled-on-timeout-tie")

    def test_cancellation_timeout_boundary_distinguishes_neighbors_from_exact_tie(self):
        timeout_ms = 22.2
        neighbor_offset_ms = 1e-9
        just_before = reference_budget(
            jitter_scale=2,
            cancel_at_ms=timeout_ms - neighbor_offset_ms,
        )
        exact = reference_budget(jitter_scale=2, cancel_at_ms=timeout_ms)
        just_after = reference_budget(
            jitter_scale=2,
            cancel_at_ms=timeout_ms + neighbor_offset_ms,
        )

        self.assertEqual(
            (
                just_before["cancellation_observed"],
                just_before["timeout_observed"],
                just_before["tie_to_cancellation"],
                just_before["terminal"],
            ),
            (True, False, False, "cancelled-safe-hold-requested"),
        )
        self.assertEqual(
            (
                exact["cancellation_observed"],
                exact["timeout_observed"],
                exact["tie_to_cancellation"],
                exact["terminal"],
            ),
            (True, True, True, "cancelled-on-timeout-tie"),
        )
        self.assertEqual(
            (
                just_after["cancellation_observed"],
                just_after["timeout_observed"],
                just_after["tie_to_cancellation"],
                just_after["terminal"],
            ),
            (False, True, False, "timed-out-safe-hold-requested"),
        )
        self.assertTrue(
            math.isclose(
                just_before["terminal_time_ms"],
                timeout_ms - neighbor_offset_ms,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )
        self.assertAlmostEqual(exact["terminal_time_ms"], timeout_ms)
        self.assertAlmostEqual(just_after["terminal_time_ms"], timeout_ms)

    def test_missing_p10_proof_recovery_and_call_isolation(self):
        blocked = reference_budget(p10_activation_proof=False)
        self.assertFalse(any(blocked["started"]))
        self.assertFalse(any(blocked["completed"]))
        assert_nan_suffix(self, blocked["actual_latency_ms"], 0)
        self.assertTrue(all(math.isfinite(value) for value in blocked["planned_latency_ms"]))
        self.assertFalse(blocked["strict_accepted"])
        self.assertFalse(blocked["reported_accepted"])
        self.assertFalse(blocked["safe_hold_requested"])
        self.assertEqual(blocked["terminal"], "blocked-p10-activation-proof")

        baseline = reference_budget()
        for _prior in (
            reference_budget(cancel_at_ms=15),
            reference_budget(jitter_scale=2),
            blocked,
            reference_budget(jitter_scale=2, assessment_mode="rss-uncorrelated"),
        ):
            self.assertEqual(reference_budget(), baseline)
        mutated = copy.deepcopy(baseline)
        mutated["planned_latency_ms"][0] = -999
        self.assertEqual(reference_budget(), baseline)
        self.assertNotEqual(mutated, baseline)

    def test_independent_oracle_rejects_malformed_inputs(self):
        bad_calls = (
            {"transport_nominal_ms": [1.2, 1.3]},
            {"transport_nominal_ms": math.nan},
            {"transport_nominal_ms": math.inf},
            {"transport_nominal_ms": True},
            {"jitter_scale": [1, 2]},
            {"jitter_scale": -1},
            {"jitter_scale": 2.1},
            {"deadline_ms": 0},
            {"deadline_ms": 10.1},
            {"deadline_ms": math.inf},
            {"p10_activation_proof": 2},
            {"p10_activation_proof": [True, False]},
            {"cancel_at_ms": -1},
            {"cancel_at_ms": -math.inf},
            {"cancel_at_ms": math.nan},
            {"cancel_at_ms": [15, 16]},
            {"cancel_at_ms": "15"},
            {"assessment_mode": "mean-only"},
            {"assessment_mode": ["bounded-sum"]},
        )
        for kwargs in bad_calls:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                reference_budget(**kwargs)
        self.assertEqual(reference_budget(p10_activation_proof=1), reference_budget())
        self.assertEqual(
            reference_budget(assessment_mode=" RSS-UNCORRELATED ")["reported_pass"],
            reference_budget(assessment_mode="rss-uncorrelated")["reported_pass"],
        )

    def test_experiment_has_ordered_baseline_two_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        section_names = re.findall(r"^%% (.+)$", experiment, flags=re.MULTILINE)
        expected_order = (
            "P11 - Budget Latency and Jitter",
            "Baseline - read the elapsed-time trace before changing a lever",
            "Complementary baseline view - inspect cumulative stage ownership",
            "Sweep 1 - move only nominal command-transport latency",
            "Read and explain lever 1 before advancing",
            "Sweep 2 - reset transport and move only jitter scale",
            "Read and explain lever 2 before advancing",
            "Negative cases - unavailable proof, cancellation, timeout, and recovery",
            "Deliberately broken case - assume unproven stage independence",
            "Check and teach back",
        )
        self.assertEqual(tuple(section_names), expected_order)
        self.assertEqual(experiment.count("figure('Name'"), 5)
        self.assertEqual(len(re.findall(r"^%% Sweep ", experiment, re.MULTILINE)), 2)
        for marker in (
            "transportSweepMs = [0.6 1.2 1.8 2.4]",
            "jitterScaleSweep = [0 0.5 1.0 1.5 2.0]",
            "Sweep 1 must hold jitter, deadline, P10 proof, event, and policy fixed",
            "Sweep 2 must reset transport and hold deadline, P10 proof, event, and policy fixed",
            "Mechanism after lever 1",
            "Mechanism after lever 2",
            "blocked = model",
            "cancelled = model",
            "timedOut = model",
            "tied = model",
            "strictCase = model",
            "broken = model",
            "rss-uncorrelated",
            "falseApproval",
            "recovered",
            "xlabel('Scheduled cycle (-)')",
            "ylabel('End-to-end latency (ms)')",
            "ylabel('Cumulative elapsed time after release (ms)')",
            "ylabel('Worst-case deadline margin (ms)')",
        ):
            self.assertIn(marker, experiment)

    def test_launch_path_asks_one_prediction_and_preserves_read_context(self):
        launch_sources = self.read("lesson.m") + "\n" + self.read("experiment.m")
        self.assertEqual(launch_sources.lower().count("prediction:"), 1)
        self.assertEqual(self.read("lesson.m").count("experiment;"), 1)
        self.assertNotIn("clc", launch_sources.lower())
        self.assertLess(
            launch_sources.index("P10 proved logical"),
            launch_sources.index("Prediction:"),
        )
        self.assertLess(
            launch_sources.index("Prediction:"),
            launch_sources.index("%% Baseline"),
        )

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        for marker in (
            "uifigure(",
            "uiaxes(",
            "transportControl = uispinner",
            "'Limits',[0.6 2.4]",
            "jitterControl = uispinner",
            "'Limits',[0 2]",
            "deadlineControl = uispinner",
            "'Limits',[0.5 10]",
            "p10ProofControl = uicheckbox",
            "cancelControl = uicheckbox",
            "cancelTimeControl = uispinner",
            "'Limits',[0 72]",
            "assessmentControl = uidropdown",
            "'bounded-sum','rss-uncorrelated'",
            "ValueChangedFcn",
            "resetButton",
            "modelFcn = @model",
            "Offline plan versus completed-cycle evidence",
            "Cumulative nominal and bounded envelope",
            "End-to-end latency (ms)",
            "Scheduled cycle (-)",
            "SAFE-HOLD requested",
            "rollback evidence available",
            "One ideal time base only: no P12 synchronization claim",
        ):
            self.assertIn(marker, interactive)
        reset_body = interactive[interactive.index("function resetBaseline") :]
        for marker in (
            "transportControl.Value = 1.2",
            "jitterControl.Value = 1.0",
            "deadlineControl.Value = 4.2",
            "p10ProofControl.Value = true",
            "cancelControl.Value = false",
            "cancelTimeControl.Value = 15.0",
            "assessmentControl.Value = 'bounded-sum'",
        ):
            self.assertIn(marker, reset_body)

    def test_learner_artifacts_are_concept_first_and_preserve_boundaries(self):
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
            "P01",
            "P10",
            "P12",
            "input",
            "observable",
            "failure",
            "nominal",
            "jitter allocation",
            "deadline",
            "margin",
            "millisecond",
            "cancellation",
            "timeout",
            "SAFE-HOLD",
            "rollback",
            "recovery",
            "independence",
            "root-sum-square",
            "interpretation",
            "teach-back",
        ):
            self.assertIn(marker.lower(), combined.lower())
        flattened = re.sub(r"\s+", " ", combined)
        self.assertIn("Deadline equality is on time", flattened)
        self.assertIn("one ideal time base", flattened.lower())
        self.assertIn("not evidence that SAFE-HOLD", flattened)
        self.assertIn("P01 introduces a seeded Gaussian/P99", flattened)
        self.assertIn("P12 owns distributed clocks", flattened)
        self.assertIn("MATLAB syntax is not part of the answer", flattened)

    def test_checks_cover_exact_oracles_malformed_events_and_isolation(self):
        checks = self.read("run_checks.m")
        for marker in (
            "expectedStageNames",
            "expectedNominalStageMs",
            "expectedBaseAllocationMs",
            "expectedPattern",
            "expectedStageVariationMs",
            "expectedLatencyMs",
            "expectedReleaseMs",
            "expectedDeadlineMs",
            "transportSweepMs",
            "expectedTransportUpperMs",
            "jitterScaleSweep",
            "expectedJitterUpperMs",
            "zeroJitter",
            "exactDeadline",
            "blocked",
            "cancelled",
            "cancelledBeforeStart",
            "cancelAfterSchedule",
            "completionTied",
            "timedOut",
            "tied",
            "justBeforeTimeoutTie",
            "justAfterTimeoutTie",
            "strictCase",
            "broken",
            "expectedBrokenLatencyMs",
            "P11:InvalidTransportNominal",
            "P11:InvalidJitterScale",
            "P11:InvalidDeadline",
            "P11:InvalidP10ActivationProof",
            "P11:InvalidCancellationTime",
            "P11:InvalidAssessmentMode",
            "afterMalformed",
            "afterCancellation",
            "afterTimeout",
            "afterBlocked",
            "afterBroken",
            "afterMutation",
            "assertTimingInvariant",
            "actualCompletionMs",
            "actualStageCompletionMs",
            "plannedStageCompletionMs",
            "stageCellCount == 48",
            "rollbackEvidenceAvailable",
            "P11 checks passed",
        ):
            self.assertIn(marker, checks)

    def test_p10_adapter_is_consumed_without_reimplementation(self):
        p10_model = (
            ROOT / "modules/10-model-system-states-and-transitions/model.m"
        ).read_text(encoding="utf-8")
        for prerequisite_fact in (
            "transitionTableAllowed",
            "strictGuardPass",
            "strictPostconditionPass",
            "priorityViolation",
        ):
            self.assertIn(prerequisite_fact, p10_model)
        event_assignment = re.search(
            r"eventNames\s*=\s*\{(.*?)\};", p10_model, flags=re.DOTALL
        )
        self.assertIsNotNone(event_assignment)
        p10_nominal_events = re.findall(r"'([^']+)'", event_assignment.group(1))
        self.assertEqual(p10_nominal_events[5], "activate-request")

        model = self.read("model.m")
        flattened = re.sub(r"\s+", " ", model)
        self.assertIn(
            "p10ActivationProof = transitionTableAllowed(p10ActivationStep) && ...",
            model,
        )
        self.assertIn("p10ActivationStep = 6", model)
        self.assertIn("strictGuardPass(p10ActivationStep)", flattened)
        self.assertIn("strictPostconditionPass(p10ActivationStep)", flattened)
        self.assertIn("~priorityViolation(p10ActivationStep)", flattened)
        self.assertIn("P11 does not invoke or reimplement the P10 state machine", model)
        self.assertIn("safeHoldRequested", model)
        self.assertIn("rollbackEvidenceAvailable = false", model)
        self.assertIn("rollbackAuthority = 'P10'", model)
        for forbidden in (
            "addpath(",
            "run_module_checks",
            "readinessConfirmations",
            "recoveryConfirmations",
            "transitionTable =",
            "stateNames =",
        ):
            self.assertNotIn(forbidden, model)

    def test_every_supported_terminal_is_behaviorally_reachable(self):
        cases = (
            reference_budget(),
            reference_budget(p10_activation_proof=False),
            reference_budget(cancel_at_ms=15),
            reference_budget(jitter_scale=2),
            reference_budget(jitter_scale=2, cancel_at_ms=22.2),
        )
        self.assertEqual(
            {case["terminal"] for case in cases},
            {
                "completed-within-budget",
                "blocked-p10-activation-proof",
                "cancelled-safe-hold-requested",
                "timed-out-safe-hold-requested",
                "cancelled-on-timeout-tie",
            },
        )

    def test_cli_lifecycle_resolves_p11_identity_without_frontier_assumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            shutil.copytree(P11, fixture / self.module["folder"])
            (fixture / "curriculum").mkdir(parents=True)
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            started = subprocess.run(
                [str(fixture / "bin/learn"), "start", "P11"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            checked = subprocess.run(
                [str(fixture / "bin/learn"), "check", "P11"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn("P11 — Budget Latency and Jitter", started.stdout)
            self.assertIn(f"Guiding question: {QUESTION}", started.stdout)
            self.assertIn("launch_lesson('P11')", started.stdout)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("run_module_checks('P11')", checked.stdout)
            state = json.loads(
                (fixture / ".learning/progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P11")
            self.assertEqual(state["completed"], {})
            self.assertEqual(state["notes"], {})

    def test_rollback_fixture_recovers_persisted_p11_to_p10_without_erasure(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 11:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            retained_note = "P11 additive timing teach-back retained"
            (state_dir / "progress.json").write_text(
                json.dumps(
                    {
                        "current": "P11",
                        "completed": {"P11": True},
                        "notes": {"P11": retained_note},
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
            implemented_count = sum(
                module["status"] == "implemented" for module in manifest["modules"]
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn("P10 — Model System States and Transitions", recovered.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn(
                f"{manifest['module_count']} total, {implemented_count} implemented, 0 completed",
                status.stdout,
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            p11_line = next(line for line in listing.stdout.splitlines() if " P11 " in line)
            self.assertTrue(p11_line.startswith("○ P11"), p11_line)
            self.assertNotIn("✓ P11", listing.stdout)
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P10")
            self.assertTrue(state["completed"]["P11"])
            self.assertEqual(state["notes"]["P11"], retained_note)

    def test_retained_evidence_has_required_sections_and_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P11-*.md"))
        self.assertTrue(evidence_files)
        evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence_files)
        for marker in (
            "Acceptance mapping",
            "Exact commands and results",
            "Figure, control, metric, and unit inventory",
            "Runtime inventory",
            "Resource envelope and profile applicability",
            "Changed invariants",
            "Preserved invariants",
            "Residual risks",
            "Rollback",
            "Unperformed validation",
            "Static",
            "simulated",
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
            "release",
            "deployment",
            "staging",
            "production",
            "post-change CI",
        ):
            self.assertIn(marker, evidence)


if __name__ == "__main__":
    unittest.main()
