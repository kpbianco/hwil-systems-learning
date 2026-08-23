from __future__ import annotations

import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P02 = ROOT / "modules/02-write-a-conops-from-an-operator-goal"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you write a CONOPS "
    "from an Operator Goal?"
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


def reference_transaction(
    command_ms: float,
    action_ms: float,
    feedback_ms: float,
    deadline_ms: float,
    feedback_available: bool = True,
    cancel_ms: float = math.inf,
) -> dict[str, object]:
    """Independent static oracle for the documented P02 event contract."""
    planned_command = float(command_ms)
    planned_effect = planned_command + float(action_ms)
    planned_feedback = planned_effect + float(feedback_ms)
    available_feedback = planned_feedback if feedback_available else math.inf
    if cancel_ms <= min(available_feedback, deadline_ms):
        state = "cancelled-safe-hold"
        terminal = float(cancel_ms)
        cancelled = True
        confirmed = False
    elif feedback_available and available_feedback <= deadline_ms:
        state = "confirmed"
        terminal = available_feedback
        cancelled = False
        confirmed = True
    else:
        state = "timeout-safe-hold"
        terminal = float(deadline_ms)
        cancelled = False
        confirmed = False
    if cancelled:
        command_occurred = planned_command < terminal
        effect_occurred = planned_effect < terminal
    else:
        command_occurred = planned_command <= terminal
        effect_occurred = planned_effect <= terminal
    return {
        "planned_command": planned_command,
        "planned_effect": planned_effect,
        "planned_feedback": planned_feedback,
        "actual_command": planned_command if command_occurred else math.inf,
        "actual_effect": planned_effect if effect_occurred else math.inf,
        "actual_feedback": planned_feedback if confirmed else math.inf,
        "terminal": terminal,
        "state": state,
        "physical": effect_occurred,
        "confirmed": confirmed,
        "safe_hold": not confirmed,
        "achieved_margin": deadline_ms - terminal if confirmed else math.nan,
    }


class P02ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P02")

    def read(self, name: str) -> str:
        return (P02 / name).read_text(encoding="utf-8")

    def test_permanent_identity_and_complete_artifact_set(self):
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
                "number": 2,
                "id": "P02",
                "title": "Write a CONOPS from an Operator Goal",
                "guiding_question": QUESTION,
                "phase": 1,
                "phase_title": "Mission and behavior",
                "slug": "write-a-conops-from-an-operator-goal",
                "folder": "modules/02-write-a-conops-from-an-operator-goal",
                "implementation_batch": "P02",
                "prerequisites": ["P01"],
            },
        )
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P02.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_placeholder_residue_and_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            path = P02 / name
            with self.subTest(path=name):
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                lowered = content.lower()
                for residue in ("scaffolded", "activate its governed", "todo", "placeholder"):
                    self.assertNotIn(residue, lowered)

    def test_model_is_deterministic_presentation_free_and_resource_bounded(self):
        model = self.read("model.m")
        compact = re.sub(r"\s+", " ", model)
        self.assertIn("function out = model(", model)
        self.assertIn("maxHorizonMs = 600000", model)
        self.assertRegex(
            compact,
            r"plannedEffectReachedMs = plannedCommandReceiptMs \+ actionDurationMs;",
        )
        self.assertRegex(
            compact,
            r"plannedFeedbackArrivalMs = plannedEffectReachedMs \+ feedbackLatencyMs;",
        )
        self.assertIn("cancelAtMs <= firstNoncancelEventMs", model)
        self.assertIn("availableFeedbackArrivalMs <= decisionDeadlineMs", model)
        self.assertLess(
            model.index("if cancelAtMs <= firstNoncancelEventMs"),
            model.index("elseif feedbackAvailable && availableFeedbackArrivalMs"),
        )
        self.assertIn("physicalGoalReached = plannedEffectReachedMs < terminalTimeMs", model)
        self.assertIn("physicalGoalReached = plannedEffectReachedMs <= terminalTimeMs", model)
        self.assertIn("safeHoldCommanded = ~confirmed", model)
        self.assertIn("actualFeedbackArrivalMs = Inf", model)
        self.assertIn("if feedbackObserved, actualFeedbackArrivalMs", model)
        self.assertIn("achievedConfirmationMarginMs = NaN", model)
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
            "sim(",
        ):
            self.assertNotIn(forbidden, model.lower())

    def test_independent_reference_oracle_covers_critical_model_branches(self):
        baseline = reference_transaction(12, 25, 18, 80)
        self.assertEqual(
            (baseline["planned_effect"], baseline["actual_feedback"], baseline["state"]),
            (37.0, 55.0, "confirmed"),
        )
        self.assertEqual(baseline["achieved_margin"], 25.0)

        zero = reference_transaction(0, 0, 0, 1)
        exact_deadline = reference_transaction(12, 25, 43, 80)
        self.assertEqual(zero["terminal"], 0.0)
        self.assertTrue(exact_deadline["confirmed"])

        feedback_loss = reference_transaction(12, 25, 18, 80, False)
        late_feedback = reference_transaction(12, 25, 50, 60)
        for failed in (feedback_loss, late_feedback):
            self.assertTrue(failed["physical"])
            self.assertFalse(failed["confirmed"])
            self.assertTrue(failed["safe_hold"])
            self.assertTrue(math.isinf(failed["actual_feedback"]))
            self.assertTrue(math.isnan(failed["achieved_margin"]))

        cancel_zero = reference_transaction(12, 25, 18, 80, True, 0)
        cancel_tie = reference_transaction(12, 25, 18, 80, True, 55)
        cancel_after = reference_transaction(12, 25, 18, 80, True, 56)
        self.assertTrue(math.isinf(cancel_zero["actual_command"]))
        self.assertTrue(math.isinf(cancel_zero["actual_effect"]))
        self.assertEqual(cancel_tie["state"], "cancelled-safe-hold")
        self.assertEqual(cancel_after["state"], "confirmed")

        more_command = reference_transaction(22, 25, 18, 80)
        more_feedback = reference_transaction(12, 25, 28, 80)
        self.assertEqual(more_command["planned_effect"] - baseline["planned_effect"], 10)
        self.assertEqual(more_command["planned_feedback"] - baseline["planned_feedback"], 10)
        self.assertEqual(more_feedback["planned_effect"], baseline["planned_effect"])
        self.assertEqual(more_feedback["planned_feedback"] - baseline["planned_feedback"], 10)

    def test_timeout_tie_has_behavioral_coverage_for_cancellation_priority(self):
        timeout_tie = reference_transaction(12, 25, 18, 80, False, 80)
        self.assertEqual(
            (
                timeout_tie["state"],
                timeout_tie["terminal"],
                timeout_tie["physical"],
                timeout_tie["confirmed"],
                timeout_tie["safe_hold"],
            ),
            ("cancelled-safe-hold", 80.0, True, False, True),
        )

        checks = self.read("run_checks.m")
        self.assertIn(
            "cancelTimeoutTie = model(12,25,18,80,false,80);",
            checks,
        )
        self.assertIn("Cancellation must have safety priority when tied with timeout", checks)

    def test_experiment_has_baseline_two_isolated_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sections), 2)
        self.assertIn("commandSweepMs = [0 12 35 55]", experiment)
        self.assertIn("feedbackSweepMs = [0 18 40 55]", experiment)
        self.assertIn("all(effectByFeedbackMs == effectByFeedbackMs(1))", experiment)
        self.assertIn("broken = model(12,25,18,80,false,Inf)", experiment)
        self.assertIn("Broken assumption", experiment)
        self.assertGreaterEqual(experiment.count("figure("), 4)
        self.assertGreaterEqual(experiment.count("xlabel("), 2)
        self.assertGreaterEqual(experiment.count("ylabel("), 4)
        self.assertGreaterEqual(experiment.count("(ms)"), 5)
        self.assertIn("Mechanism after lever 1", experiment)
        self.assertLess(experiment.index("Mechanism after lever 1"), experiment.index("%% Sweep 2"))
        self.assertLess(
            experiment.index("Mechanism after lever 2"), experiment.index("%% Broken case")
        )

    def test_interactive_controls_are_bounded_and_keep_the_p02_model_bound(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertIn("uislider", interactive)
        self.assertIn("'Limits',[0 80]", interactive)
        self.assertIn("'Limits',[0 100]", interactive)
        self.assertIn("'Limits',[1 200]", interactive)
        self.assertIn("uicheckbox", interactive)
        self.assertIn("uidropdown", interactive)
        self.assertIn("cancel.ItemsData = [Inf 0 20 40 80]", interactive)
        self.assertIn("resetBaseline", interactive)
        self.assertGreaterEqual(interactive.count("ValueChangingFcn"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 5)
        self.assertIn("Occurred events; deadline is the decision reference", interactive)
        self.assertIn("planned margin", interactive)
        self.assertIn("achieved margin", interactive)

    def test_checks_cover_limits_failures_recovery_isolation_and_compatibility(self):
        checks = self.read("run_checks.m")
        self.assertGreaterEqual(checks.count("assert("), 25)
        for marker in (
            "zeroLimit",
            "exactDeadline",
            "moreCommand",
            "moreFeedback",
            "feedbackLoss",
            "operationalRecovery",
            "lateFeedback",
            "cancelBeforeCommand",
            "cancelDuringAction",
            "cancelAfterEffect",
            "cancelTie",
            "cancelTimeoutTie",
            "cancelAfterConfirmation",
            "uint16",
            "P02:InvalidFeedbackFlag",
            "P02:InvalidCancelTime",
            "P02:ResourceBound",
            "recovered",
            "isequaln(baseline,repeat)",
            "actualFeedbackArrivalMs",
            "timelineSlotCount",
            "occurredEventCount",
        ):
            self.assertIn(marker, checks)
        self.assertIn("P02 checks passed", checks)

    def test_lesson_is_concept_first_compounds_on_p01_and_requires_teach_back(self):
        combined = "\n".join(
            self.read(name) for name in ("README.md", "lesson.m", "lesson.md", "walkthrough.md", "checks.md")
        )
        self.assertGreaterEqual(combined.count(QUESTION), 3)
        self.assertIn("P01", combined)
        self.assertIn("command-path latency + physical-action duration", combined)
        self.assertIn("observability", combined.lower())
        self.assertIn("timeout", combined.lower())
        self.assertIn("cancellation", combined.lower())
        self.assertIn("recovery", combined.lower())
        self.assertIn("teach-back", combined.lower())
        self.assertIn("interpretation questions", combined.lower())
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_retained_evidence_exists_and_states_the_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P02-*.md"))
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
