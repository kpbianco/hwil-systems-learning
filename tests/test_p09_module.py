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
P09 = ROOT / "modules/09-design-startup-and-shutdown-sequences"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you design "
    "Startup and Shutdown Sequences?"
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
STARTUP_BASE = [
    "assert-command-inhibit",
    "energize-power",
    "boot-controller",
    "qualify-p08-interface",
    "release-command-inhibit",
]
SHUTDOWN_BASE = [
    "inhibit-new-commands",
    "command-safe-output",
    "disable-actuator",
    "confirm-quiescence",
    "close-p08-interface",
]
ROLLBACK_ACTIONS = [
    "inhibit-new-commands",
    "command-safe-output",
    "disable-actuator",
    "confirm-quiescence-and-isolate",
    "remove-power",
]
STATE_NAMES = [
    "Power on",
    "Controller online",
    "P08 interface qualified",
    "Actuator enabled",
    "Command inhibited",
    "Safe command asserted",
    "Quiescence confirmed",
]


def insert_action(base: list[str], action: str, one_based_position: int) -> list[str]:
    index = one_based_position - 1
    return [*base[:index], action, *base[index:]]


def state_vector(state: dict[str, bool]) -> list[int]:
    return [
        int(state["power"]),
        int(state["controller"]),
        int(state["interface"]),
        int(state["actuator"]),
        int(state["inhibited"]),
        int(state["safe_command"]),
        int(state["quiescent"]),
    ]


def reference_sequence(
    startup_enable_position: int = 5,
    shutdown_power_position: int = 6,
    p08_conformant: bool = True,
    p08_eligible: bool = True,
    fault_mode: str = "none",
    event_mode: str = "none",
    assessment_mode: str = "strict-order",
) -> dict[str, object]:
    """Independent Python oracle for the documented fixed P09 lifecycle."""
    if p08_eligible and not p08_conformant:
        raise ValueError("P08 eligibility implies conformance")

    action_count = 6
    state_count = 7
    event_checkpoint = 3
    startup_actions = insert_action(
        STARTUP_BASE, "enable-actuator", startup_enable_position
    )
    shutdown_actions = insert_action(
        SHUTDOWN_BASE, "remove-power", shutdown_power_position
    )
    cancellation = event_mode in {"cancellation", "cancellation-timeout-tie"}
    timeout = event_mode in {"timeout", "cancellation-timeout-tie"}
    event_observed = cancellation or timeout

    state = {
        "power": False,
        "controller": False,
        "interface": False,
        "actuator": False,
        "inhibited": True,
        "safe_command": True,
        "quiescent": True,
    }
    startup_evaluated = [False] * action_count
    startup_pre = [False] * action_count
    startup_post = [False] * action_count
    startup_step = [False] * action_count
    startup_hazard = [False] * action_count
    startup_trace = [[math.nan] * state_count for _ in range(action_count)]
    startup_enable_prerequisites = [False] * 6

    for index, action in enumerate(startup_actions):
        if event_observed and index >= event_checkpoint:
            break
        startup_evaluated[index] = True
        if action == "assert-command-inhibit":
            pre = True
            state["inhibited"] = True
            state["safe_command"] = True
            post = state["inhibited"] and state["safe_command"]
        elif action == "energize-power":
            pre = (
                state["inhibited"]
                and state["safe_command"]
                and not state["actuator"]
            )
            state["power"] = True
            post = state["power"]
        elif action == "boot-controller":
            pre = state["power"] and state["inhibited"]
            state["controller"] = True
            post = state["controller"]
        elif action == "qualify-p08-interface":
            pre = state["power"] and state["controller"] and p08_conformant
            state["interface"] = (
                state["power"] and state["controller"] and p08_conformant
            )
            post = state["interface"]
        elif action == "enable-actuator":
            startup_enable_prerequisites = [
                state["power"],
                state["controller"],
                state["interface"],
                p08_eligible,
                state["inhibited"],
                state["safe_command"],
            ]
            pre = all(startup_enable_prerequisites)
            state["actuator"] = True
            state["quiescent"] = False
            post = state["actuator"]
        elif action == "release-command-inhibit":
            pre = (
                state["power"]
                and state["controller"]
                and state["interface"]
                and p08_eligible
                and state["actuator"]
                and state["inhibited"]
                and state["safe_command"]
            )
            state["inhibited"] = False
            state["safe_command"] = False
            post = not state["inhibited"] and not state["safe_command"]
        else:  # pragma: no cover - fixed action inventory
            raise AssertionError(action)
        startup_pre[index] = pre
        startup_post[index] = post
        startup_step[index] = pre and post
        startup_hazard[index] = not startup_step[index]
        startup_trace[index] = state_vector(state)

    startup_completed = all(startup_evaluated)
    startup_final_state = state_vector(state)
    startup_final_running = (
        startup_completed
        and state["power"]
        and state["controller"]
        and state["interface"]
        and p08_eligible
        and state["actuator"]
        and not state["inhibited"]
        and not state["safe_command"]
    )
    startup_order_valid = startup_completed and all(startup_step)
    enable_index = startup_enable_position - 1
    startup_missing = (
        sum(not fact for fact in startup_enable_prerequisites)
        if startup_evaluated[enable_index]
        else None
    )

    rollback_executed = [False] * len(ROLLBACK_ACTIONS)
    rollback_pre = [False] * len(ROLLBACK_ACTIONS)
    rollback_post = [False] * len(ROLLBACK_ACTIONS)
    rollback_step = [False] * len(ROLLBACK_ACTIONS)
    rollback_hazard = [False] * len(ROLLBACK_ACTIONS)
    rollback_trace = [[math.nan] * state_count for _ in ROLLBACK_ACTIONS]
    rollback_performed = False
    rollback_safe_hold = False

    shutdown_evaluated = [False] * action_count
    shutdown_pre = [False] * action_count
    shutdown_post = [False] * action_count
    shutdown_step = [False] * action_count
    shutdown_hazard = [False] * action_count
    shutdown_trace = [[math.nan] * state_count for _ in range(action_count)]
    shutdown_power_prerequisites = [False] * 5
    unsafe_power_removal = False

    if event_observed:
        rollback_performed = True
        for index, action in enumerate(ROLLBACK_ACTIONS):
            rollback_executed[index] = True
            if action == "inhibit-new-commands":
                pre = True
                state["inhibited"] = True
                post = state["inhibited"]
            elif action == "command-safe-output":
                pre = state["inhibited"]
                state["safe_command"] = True
                post = state["safe_command"]
            elif action == "disable-actuator":
                pre = state["inhibited"] and state["safe_command"]
                if fault_mode != "actuator-stuck-on":
                    state["actuator"] = False
                post = not state["actuator"]
            elif action == "confirm-quiescence-and-isolate":
                pre = (
                    state["inhibited"]
                    and state["safe_command"]
                    and not state["actuator"]
                )
                state["quiescent"] = (
                    pre and fault_mode != "quiescence-not-confirmed"
                )
                state["interface"] = False
                state["controller"] = False
                post = (
                    state["quiescent"]
                    and not state["interface"]
                    and not state["controller"]
                )
            elif action == "remove-power":
                pre = (
                    state["inhibited"]
                    and state["safe_command"]
                    and not state["actuator"]
                    and state["quiescent"]
                    and not state["interface"]
                )
                state["power"] = False
                post = not state["power"]
            else:  # pragma: no cover - fixed action inventory
                raise AssertionError(action)
            rollback_pre[index] = pre
            rollback_post[index] = post
            rollback_step[index] = pre and post
            rollback_hazard[index] = not rollback_step[index]
            rollback_trace[index] = state_vector(state)
        rollback_safe_hold = (
            all(rollback_step)
            and not state["power"]
            and not state["controller"]
            and not state["interface"]
            and not state["actuator"]
            and state["inhibited"]
            and state["safe_command"]
            and state["quiescent"]
        )
    else:
        for index, action in enumerate(shutdown_actions):
            shutdown_evaluated[index] = True
            if action == "inhibit-new-commands":
                pre = True
                state["inhibited"] = True
                post = state["inhibited"]
            elif action == "command-safe-output":
                pre = state["inhibited"]
                state["safe_command"] = True
                post = state["safe_command"]
            elif action == "disable-actuator":
                pre = state["inhibited"] and state["safe_command"]
                if fault_mode != "actuator-stuck-on":
                    state["actuator"] = False
                post = not state["actuator"]
            elif action == "confirm-quiescence":
                pre = (
                    state["inhibited"]
                    and state["safe_command"]
                    and not state["actuator"]
                )
                state["quiescent"] = (
                    pre and fault_mode != "quiescence-not-confirmed"
                )
                post = state["quiescent"]
            elif action == "close-p08-interface":
                pre = (
                    state["inhibited"]
                    and not state["actuator"]
                    and state["quiescent"]
                )
                state["interface"] = False
                post = not state["interface"]
            elif action == "remove-power":
                shutdown_power_prerequisites = [
                    state["inhibited"],
                    state["safe_command"],
                    not state["actuator"],
                    state["quiescent"],
                    not state["interface"],
                ]
                pre = all(shutdown_power_prerequisites)
                unsafe_power_removal = not pre
                state["power"] = False
                state["controller"] = False
                post = not state["power"] and not state["controller"]
            else:  # pragma: no cover - fixed action inventory
                raise AssertionError(action)
            shutdown_pre[index] = pre
            shutdown_post[index] = post
            shutdown_step[index] = pre and post
            shutdown_hazard[index] = not shutdown_step[index]
            shutdown_trace[index] = state_vector(state)

    shutdown_completed = all(shutdown_evaluated)
    shutdown_final_state = (
        state_vector(state) if shutdown_completed else [math.nan] * state_count
    )
    shutdown_final_safe_off = (
        shutdown_completed
        and not state["power"]
        and not state["controller"]
        and not state["interface"]
        and not state["actuator"]
        and state["inhibited"]
        and state["safe_command"]
        and state["quiescent"]
    )
    shutdown_order_valid = shutdown_completed and all(shutdown_step)
    power_index = shutdown_power_position - 1
    shutdown_missing = (
        sum(not fact for fact in shutdown_power_prerequisites)
        if shutdown_evaluated[power_index]
        else None
    )

    sequence_evaluated = startup_completed and shutdown_completed
    strict_accepted = (
        sequence_evaluated
        and startup_order_valid
        and startup_final_running
        and shutdown_order_valid
        and shutdown_final_safe_off
    )
    snapshot_accepted = (
        sequence_evaluated and startup_final_running and shutdown_final_safe_off
    )
    reported_accepted = (
        strict_accepted if assessment_mode == "strict-order" else snapshot_accepted
    )
    false_approval = sequence_evaluated and reported_accepted and not strict_accepted
    decision_correct = (
        sequence_evaluated and reported_accepted == strict_accepted
    )
    startup_violations = sum(
        evaluated and not passed
        for evaluated, passed in zip(startup_evaluated, startup_step)
    )
    shutdown_violations = sum(
        evaluated and not passed
        for evaluated, passed in zip(shutdown_evaluated, shutdown_step)
    )
    rollback_violations = sum(
        executed and not passed
        for executed, passed in zip(rollback_executed, rollback_step)
    )

    if cancellation and rollback_safe_hold:
        terminal = "cancelled-safe-hold"
    elif cancellation:
        terminal = "cancelled-rollback-incomplete"
    elif timeout and rollback_safe_hold:
        terminal = "timed-out-safe-hold"
    elif timeout:
        terminal = "timed-out-rollback-incomplete"
    elif strict_accepted:
        terminal = "completed-safe-off"
    else:
        terminal = "completed-with-hazard"

    if cancellation:
        failure = "startup-cancelled"
    elif timeout:
        failure = "startup-timeout"
    elif not p08_conformant:
        failure = "p08-contract-not-conformant"
    elif not p08_eligible:
        failure = "p08-input-not-eligible"
    elif not startup_pre[enable_index]:
        failure = "startup-enable-before-prerequisites"
    elif not startup_order_valid or not startup_final_running:
        failure = "startup-sequence-invalid"
    elif fault_mode == "actuator-stuck-on":
        failure = "actuator-disable-failed"
    elif fault_mode == "quiescence-not-confirmed":
        failure = "quiescence-not-confirmed"
    elif unsafe_power_removal:
        failure = "power-removed-before-safe"
    elif not shutdown_order_valid or not shutdown_final_safe_off:
        failure = "shutdown-sequence-invalid"
    else:
        failure = "none"

    if not event_observed or rollback_safe_hold:
        rollback_failure = "none"
    elif not rollback_post[2]:
        rollback_failure = "actuator-disable-failed"
    else:
        rollback_failure = "quiescence-not-confirmed"

    return {
        "startup_actions": startup_actions,
        "shutdown_actions": shutdown_actions,
        "startup_evaluated": startup_evaluated,
        "startup_pre": startup_pre,
        "startup_post": startup_post,
        "startup_step": startup_step,
        "startup_hazard": startup_hazard,
        "startup_trace": startup_trace,
        "startup_enable_prerequisites": startup_enable_prerequisites,
        "startup_missing": startup_missing,
        "startup_completed": startup_completed,
        "startup_final_state": startup_final_state,
        "startup_final_running": startup_final_running,
        "startup_order_valid": startup_order_valid,
        "shutdown_evaluated": shutdown_evaluated,
        "shutdown_pre": shutdown_pre,
        "shutdown_post": shutdown_post,
        "shutdown_step": shutdown_step,
        "shutdown_hazard": shutdown_hazard,
        "shutdown_trace": shutdown_trace,
        "shutdown_power_prerequisites": shutdown_power_prerequisites,
        "shutdown_missing": shutdown_missing,
        "unsafe_power_removal": unsafe_power_removal,
        "shutdown_completed": shutdown_completed,
        "shutdown_final_state": shutdown_final_state,
        "shutdown_final_safe_off": shutdown_final_safe_off,
        "shutdown_order_valid": shutdown_order_valid,
        "rollback_executed": rollback_executed,
        "rollback_pre": rollback_pre,
        "rollback_post": rollback_post,
        "rollback_step": rollback_step,
        "rollback_hazard": rollback_hazard,
        "rollback_trace": rollback_trace,
        "rollback_performed": rollback_performed,
        "rollback_safe_hold": rollback_safe_hold,
        "cancellation": cancellation,
        "timeout": timeout,
        "event_observed": event_observed,
        "tie_resolved_to_cancellation": event_mode
        == "cancellation-timeout-tie",
        "sequence_evaluated": sequence_evaluated,
        "strict_accepted": strict_accepted,
        "snapshot_accepted": snapshot_accepted,
        "reported_accepted": reported_accepted,
        "false_approval": false_approval,
        "decision_correct": decision_correct,
        "startup_violations": startup_violations,
        "shutdown_violations": shutdown_violations,
        "rollback_violations": rollback_violations,
        "total_violations": (
            startup_violations + shutdown_violations + rollback_violations
        ),
        "terminal": terminal,
        "failure": failure,
        "rollback_failure": rollback_failure,
        "reporting_failure": (
            "final-state-only-false-approval" if false_approval else "none"
        ),
    }


def assert_oracle_invariants(test: unittest.TestCase, result: dict[str, object]) -> None:
    test.assertEqual(len(result["startup_actions"]), 6)
    test.assertEqual(len(result["shutdown_actions"]), 6)
    test.assertEqual(len(result["startup_trace"]), 6)
    test.assertEqual(len(result["shutdown_trace"]), 6)
    test.assertEqual(len(result["rollback_trace"]), 5)
    test.assertTrue(all(len(row) == 7 for row in result["startup_trace"]))
    test.assertTrue(all(len(row) == 7 for row in result["shutdown_trace"]))
    test.assertTrue(all(len(row) == 7 for row in result["rollback_trace"]))
    for phase in ("startup", "shutdown"):
        evaluated = result[f"{phase}_evaluated"]
        pre = result[f"{phase}_pre"]
        post = result[f"{phase}_post"]
        step = result[f"{phase}_step"]
        hazard = result[f"{phase}_hazard"]
        trace = result[f"{phase}_trace"]
        test.assertEqual(
            step,
            [e and g and p for e, g, p in zip(evaluated, pre, post)],
        )
        test.assertEqual(hazard, [e and not s for e, s in zip(evaluated, step)])
        for was_evaluated, row in zip(evaluated, trace):
            if was_evaluated:
                test.assertTrue(all(math.isfinite(value) for value in row))
            else:
                test.assertTrue(all(math.isnan(value) for value in row))
    test.assertEqual(
        result["startup_order_valid"],
        result["startup_completed"] and all(result["startup_step"]),
    )
    test.assertEqual(
        result["shutdown_order_valid"],
        result["shutdown_completed"] and all(result["shutdown_step"]),
    )
    test.assertEqual(
        result["strict_accepted"],
        result["sequence_evaluated"]
        and result["startup_order_valid"]
        and result["startup_final_running"]
        and result["shutdown_order_valid"]
        and result["shutdown_final_safe_off"],
    )
    test.assertEqual(
        result["snapshot_accepted"],
        result["sequence_evaluated"]
        and result["startup_final_running"]
        and result["shutdown_final_safe_off"],
    )
    test.assertEqual(
        result["false_approval"],
        result["sequence_evaluated"]
        and result["reported_accepted"]
        and not result["strict_accepted"],
    )
    test.assertEqual(
        result["total_violations"],
        result["startup_violations"]
        + result["shutdown_violations"]
        + result["rollback_violations"],
    )
    test.assertEqual(
        result["event_observed"], result["cancellation"] or result["timeout"]
    )
    test.assertEqual(
        result["rollback_step"],
        [
            e and g and p
            for e, g, p in zip(
                result["rollback_executed"],
                result["rollback_pre"],
                result["rollback_post"],
            )
        ],
    )
    test.assertEqual(
        result["rollback_hazard"],
        [
            e and not passed
            for e, passed in zip(
                result["rollback_executed"], result["rollback_step"]
            )
        ],
    )
    if result["event_observed"]:
        test.assertTrue(result["rollback_performed"])
        test.assertTrue(all(result["rollback_executed"]))
        test.assertTrue(
            all(math.isnan(value) for value in result["shutdown_final_state"])
        )
        test.assertTrue(
            all(
                math.isfinite(value)
                for row in result["rollback_trace"]
                for value in row
            )
        )
        final_safe_hold = result["rollback_trace"][-1] == [0, 0, 0, 0, 1, 1, 1]
        test.assertEqual(
            result["rollback_safe_hold"],
            all(result["rollback_step"]) and final_safe_hold,
        )
    else:
        test.assertFalse(result["rollback_performed"])
        test.assertFalse(any(result["rollback_executed"]))
        test.assertFalse(any(result["rollback_pre"]))
        test.assertFalse(any(result["rollback_post"]))
        test.assertFalse(any(result["rollback_step"]))
        test.assertFalse(any(result["rollback_hazard"]))
        test.assertTrue(
            all(
                math.isnan(value)
                for row in result["rollback_trace"]
                for value in row
            )
        )
        test.assertFalse(result["rollback_safe_hold"])
        test.assertEqual(result["rollback_failure"], "none")
        test.assertTrue(
            all(math.isfinite(value) for value in result["shutdown_final_state"])
        )


class P09ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P09")

    def read(self, name: str) -> str:
        return (P09 / name).read_text(encoding="utf-8")

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
                "number": 9,
                "id": "P09",
                "title": "Design Startup and Shutdown Sequences",
                "guiding_question": QUESTION,
                "phase": 3,
                "phase_title": "Sequencing and synchronization",
                "slug": "design-startup-and-shutdown-sequences",
                "folder": "modules/09-design-startup-and-shutdown-sequences",
                "implementation_batch": "P09",
                "prerequisites": ["P08"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P08"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P09.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_residue_and_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            with self.subTest(path=name):
                content = self.read(name)
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
        compact = re.sub(r"\s+|\.\.\.", "", model)
        self.assertIn("function out = model(", model)
        for marker in (
            "minimumStartupEnablePosition = 1",
            "maximumStartupEnablePosition = 5",
            "minimumShutdownPowerOffPosition = 1",
            "maximumShutdownPowerOffPosition = 6",
            "actionCount = 6",
            "stateCount = 7",
            "rollbackActionCount = 5",
            "eventCheckpointAction = 3",
            "P09:InconsistentP08Facts",
        ):
            self.assertIn(marker, model)
        for fragment in (
            "startupActionNames=insertAction(startupBaseActions,'enable-actuator',startupEnablePosition);",
            "shutdownActionNames=insertAction(shutdownBaseActions,'remove-power',shutdownPowerOffPosition);",
            "startupEnablePrerequisitePass=[powerOncontrollerOnlineinterfaceQualifiedp08InputEligiblecommandInhibitedsafeCommandAsserted];",
            "shutdownPowerPrerequisitePass=[commandInhibitedsafeCommandAsserted~actuatorEnabledquiescenceConfirmed~interfaceQualified];",
            "startupStepPass(k)=preconditionPass&&postconditionPass;",
            "shutdownStepPass(k)=preconditionPass&&postconditionPass;",
            "rollbackStepPass(k)=preconditionPass&&postconditionPass;",
            "startupHazard(k)=~startupStepPass(k);",
            "shutdownHazard(k)=~shutdownStepPass(k);",
            "rollbackHazard(k)=~rollbackStepPass(k);",
            "startupFinalRunning=startupCompleted&&powerOn&&controllerOnline&&interfaceQualified&&p08InputEligible&&actuatorEnabled&&~commandInhibited&&~safeCommandAsserted;",
            "shutdownFinalSafeOff=shutdownCompleted&&~powerOn&&~controllerOnline&&~interfaceQualified&&~actuatorEnabled&&commandInhibited&&safeCommandAsserted&&quiescenceConfirmed;",
            "ifshutdownCompletedshutdownFinalState=stateVector(powerOn,controllerOnline,interfaceQualified,actuatorEnabled,commandInhibited,safeCommandAsserted,quiescenceConfirmed);elseshutdownFinalState=NaN(1,stateCount);end",
            "rollbackSafeHold=all(rollbackStepPass)&&~powerOn&&~controllerOnline&&~interfaceQualified&&~actuatorEnabled&&commandInhibited&&safeCommandAsserted&&quiescenceConfirmed;",
            "strictLifecycleAccepted=sequenceEvaluated&&startupOrderValid&&startupFinalRunning&&shutdownOrderValid&&shutdownFinalSafeOff;",
            "snapshotLifecycleAccepted=sequenceEvaluated&&startupFinalRunning&&shutdownFinalSafeOff;",
            "falseApproval=sequenceEvaluated&&reportedLifecycleAccepted&&~strictLifecycleAccepted;",
            "terminalStatus='cancelled-rollback-incomplete';",
            "terminalStatus='timed-out-rollback-incomplete';",
            "rollbackFailureMode='actuator-disable-failed';",
            "rollbackFailureMode='quiescence-not-confirmed';",
            "totalViolationCount=startupViolationCount+shutdownViolationCount+rollbackViolationCount;",
            "normalized=double(value);",
            "normalized~=round(normalized)",
            "isfinite(value)&&(value==0||value==1)",
        ):
            self.assertIn(fragment, compact)
        self.assertEqual(
            compact.count(
                "if~strcmp(faultMode,'actuator-stuck-on')actuatorEnabled=false;endpostconditionPass=~actuatorEnabled;"
            ),
            2,
        )
        self.assertIn(
            "case'confirm-quiescence-and-isolate'preconditionPass=commandInhibited&&safeCommandAsserted&&~actuatorEnabled;quiescenceConfirmed=preconditionPass&&~strcmp(faultMode,'quiescence-not-confirmed');interfaceQualified=false;controllerOnline=false;postconditionPass=quiescenceConfirmed&&~interfaceQualified&&~controllerOnline;",
            compact,
        )
        self.assertIn(
            "case'remove-power'preconditionPass=commandInhibited&&safeCommandAsserted&&~actuatorEnabled&&quiescenceConfirmed&&~interfaceQualified;powerOn=false;postconditionPass=~powerOn;",
            compact,
        )
        for error_id in (
            "P09:InvalidStartupEnablePosition",
            "P09:InvalidShutdownPowerOffPosition",
            "P09:InvalidP08Conformance",
            "P09:InvalidP08Eligibility",
            "P09:InconsistentP08Facts",
            "P09:InvalidFaultMode",
            "P09:InvalidEventMode",
            "P09:InvalidAssessmentMode",
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
            "system(",
            "intlinprog(",
            "fmincon(",
        ):
            self.assertNotIn(forbidden, model.lower())

        all_matlab = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(P09.glob("*.m"))
        ).lower()
        for opaque_or_external in (
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
            "system(",
            "unix(",
            "dos(",
            "intlinprog(",
            "optimproblem(",
            "fmincon(",
            "ga(",
        ):
            self.assertNotIn(opaque_or_external, all_matlab)

    def test_independent_oracle_baseline_and_fixed_trace(self):
        baseline = reference_sequence()
        assert_oracle_invariants(self, baseline)
        self.assertEqual(
            baseline["startup_actions"],
            [*STARTUP_BASE[:4], "enable-actuator", STARTUP_BASE[4]],
        )
        self.assertEqual(
            baseline["shutdown_actions"], [*SHUTDOWN_BASE, "remove-power"]
        )
        self.assertEqual(
            baseline["startup_trace"],
            [
                [0, 0, 0, 0, 1, 1, 1],
                [1, 0, 0, 0, 1, 1, 1],
                [1, 1, 0, 0, 1, 1, 1],
                [1, 1, 1, 0, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 0, 0, 0],
            ],
        )
        self.assertEqual(
            baseline["shutdown_trace"],
            [
                [1, 1, 1, 1, 1, 0, 0],
                [1, 1, 1, 1, 1, 1, 0],
                [1, 1, 1, 0, 1, 1, 0],
                [1, 1, 1, 0, 1, 1, 1],
                [1, 1, 0, 0, 1, 1, 1],
                [0, 0, 0, 0, 1, 1, 1],
            ],
        )
        self.assertTrue(all(baseline["startup_step"]))
        self.assertTrue(all(baseline["shutdown_step"]))
        self.assertEqual(baseline["startup_missing"], 0)
        self.assertEqual(baseline["shutdown_missing"], 0)
        self.assertEqual(baseline["startup_final_state"], [1, 1, 1, 1, 0, 0, 0])
        self.assertEqual(baseline["shutdown_final_state"], [0, 0, 0, 0, 1, 1, 1])
        self.assertTrue(baseline["strict_accepted"])
        self.assertTrue(baseline["decision_correct"])
        self.assertEqual(baseline["terminal"], "completed-safe-off")
        self.assertEqual(baseline["failure"], "none")

    def test_independent_oracle_startup_sweep_and_limits(self):
        results = [reference_sequence(startup_enable_position=p) for p in range(1, 6)]
        for result in results:
            assert_oracle_invariants(self, result)
            self.assertTrue(result["startup_final_running"])
            self.assertTrue(result["shutdown_final_safe_off"])
        self.assertEqual([result["startup_missing"] for result in results], [3, 3, 2, 1, 0])
        self.assertEqual(
            [result["strict_accepted"] for result in results],
            [False, False, False, False, True],
        )
        self.assertEqual(results[0]["failure"], "startup-enable-before-prerequisites")
        self.assertEqual(results[3]["startup_missing"], 1)
        self.assertFalse(results[3]["strict_accepted"])
        self.assertTrue(results[4]["strict_accepted"])

    def test_independent_oracle_shutdown_sweep_and_limits(self):
        results = [reference_sequence(shutdown_power_position=p) for p in range(1, 7)]
        for result in results:
            assert_oracle_invariants(self, result)
            self.assertTrue(result["startup_final_running"])
            self.assertTrue(result["shutdown_final_safe_off"])
        self.assertEqual([result["shutdown_missing"] for result in results], [5, 4, 3, 2, 1, 0])
        self.assertEqual(
            [result["strict_accepted"] for result in results],
            [False, False, False, False, False, True],
        )
        self.assertTrue(results[0]["unsafe_power_removal"])
        self.assertEqual(results[0]["failure"], "power-removed-before-safe")
        self.assertTrue(results[4]["unsafe_power_removal"])
        self.assertFalse(results[5]["unsafe_power_removal"])

    def test_independent_oracle_p08_compatibility_and_shutdown_faults(self):
        contract_invalid = reference_sequence(p08_conformant=False, p08_eligible=False)
        input_withheld = reference_sequence(p08_eligible=False)
        stuck = reference_sequence(fault_mode="actuator-stuck-on")
        not_quiet = reference_sequence(fault_mode="quiescence-not-confirmed")
        for result in (contract_invalid, input_withheld, stuck, not_quiet):
            assert_oracle_invariants(self, result)
            self.assertFalse(result["strict_accepted"])
        self.assertEqual(contract_invalid["failure"], "p08-contract-not-conformant")
        self.assertFalse(contract_invalid["startup_final_running"])
        self.assertEqual(input_withheld["failure"], "p08-input-not-eligible")
        self.assertTrue(input_withheld["startup_enable_prerequisites"][2])
        self.assertFalse(input_withheld["startup_enable_prerequisites"][3])
        self.assertEqual(stuck["failure"], "actuator-disable-failed")
        self.assertEqual(stuck["shutdown_final_state"][3], 1)
        self.assertTrue(stuck["unsafe_power_removal"])
        self.assertEqual(not_quiet["failure"], "quiescence-not-confirmed")
        self.assertEqual(not_quiet["shutdown_final_state"][6], 0)
        with self.assertRaises(ValueError):
            reference_sequence(p08_conformant=False, p08_eligible=True)

    def test_independent_oracle_cancellation_timeout_rollback_and_isolation(self):
        cancelled = reference_sequence(event_mode="cancellation")
        timed_out = reference_sequence(event_mode="timeout")
        tied = reference_sequence(event_mode="cancellation-timeout-tie")
        timeout_before_contract = reference_sequence(
            p08_conformant=False, p08_eligible=False, event_mode="timeout"
        )
        for result in (cancelled, timed_out, tied, timeout_before_contract):
            assert_oracle_invariants(self, result)
            self.assertEqual(
                result["startup_evaluated"],
                [True, True, True, False, False, False],
            )
            self.assertIsNone(result["startup_missing"])
            self.assertFalse(any(result["shutdown_evaluated"]))
            self.assertTrue(
                all(math.isnan(value) for row in result["shutdown_trace"] for value in row)
            )
            self.assertIsNone(result["shutdown_missing"])
            self.assertTrue(
                all(math.isnan(value) for value in result["shutdown_final_state"])
            )
            self.assertTrue(result["rollback_performed"])
            self.assertTrue(result["rollback_safe_hold"])
            self.assertTrue(all(result["rollback_executed"]))
            self.assertTrue(all(result["rollback_pre"]))
            self.assertTrue(all(result["rollback_post"]))
            self.assertTrue(all(result["rollback_step"]))
            self.assertFalse(any(result["rollback_hazard"]))
            self.assertEqual(result["rollback_trace"][-1], [0, 0, 0, 0, 1, 1, 1])
            self.assertEqual(result["rollback_failure"], "none")
            self.assertFalse(result["sequence_evaluated"])
            self.assertFalse(result["reported_accepted"])
            self.assertFalse(result["decision_correct"])
        self.assertEqual(cancelled["terminal"], "cancelled-safe-hold")
        self.assertEqual(cancelled["failure"], "startup-cancelled")
        self.assertEqual(timed_out["terminal"], "timed-out-safe-hold")
        self.assertEqual(timed_out["failure"], "startup-timeout")
        self.assertTrue(tied["tie_resolved_to_cancellation"])
        self.assertEqual(tied["terminal"], "cancelled-safe-hold")
        self.assertEqual(timeout_before_contract["failure"], "startup-timeout")

        early = reference_sequence(
            startup_enable_position=1,
            shutdown_power_position=1,
            event_mode="cancellation",
            assessment_mode="final-state-only",
        )
        assert_oracle_invariants(self, early)
        self.assertGreaterEqual(early["startup_violations"], 1)
        self.assertTrue(early["rollback_safe_hold"])
        self.assertFalse(early["reported_accepted"])

        cancelled_stuck = reference_sequence(
            startup_enable_position=1,
            fault_mode="actuator-stuck-on",
            event_mode="cancellation",
        )
        timed_out_not_quiet = reference_sequence(
            fault_mode="quiescence-not-confirmed",
            event_mode="timeout",
        )
        for result in (cancelled_stuck, timed_out_not_quiet):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["rollback_performed"])
            self.assertFalse(result["rollback_safe_hold"])
            self.assertTrue(any(result["rollback_hazard"]))
            self.assertGreaterEqual(result["rollback_violations"], 1)
        self.assertEqual(
            cancelled_stuck["terminal"], "cancelled-rollback-incomplete"
        )
        self.assertEqual(
            cancelled_stuck["rollback_failure"], "actuator-disable-failed"
        )
        self.assertEqual(
            cancelled_stuck["rollback_trace"][-1], [0, 0, 0, 1, 1, 1, 0]
        )
        self.assertEqual(
            timed_out_not_quiet["terminal"], "timed-out-rollback-incomplete"
        )
        self.assertEqual(
            timed_out_not_quiet["rollback_failure"],
            "quiescence-not-confirmed",
        )
        self.assertEqual(
            timed_out_not_quiet["rollback_trace"][-1], [0, 0, 0, 0, 1, 1, 0]
        )

    def test_event_isolation_and_cancellation_tie_survive_failed_rollback(self):
        scenarios = {
            "cancellation": reference_sequence(
                fault_mode="quiescence-not-confirmed",
                event_mode="cancellation",
            ),
            "timeout": reference_sequence(
                fault_mode="quiescence-not-confirmed",
                event_mode="timeout",
            ),
            "tie": reference_sequence(
                fault_mode="quiescence-not-confirmed",
                event_mode="cancellation-timeout-tie",
            ),
        }
        for event, result in scenarios.items():
            with self.subTest(event=event):
                assert_oracle_invariants(self, result)
                self.assertFalse(any(result["shutdown_evaluated"]))
                self.assertTrue(
                    all(
                        math.isnan(value)
                        for value in result["shutdown_final_state"]
                    )
                )
                self.assertFalse(result["rollback_safe_hold"])
                self.assertEqual(
                    result["rollback_failure"], "quiescence-not-confirmed"
                )
                self.assertEqual(
                    result["rollback_trace"][-1], [0, 0, 0, 0, 1, 1, 0]
                )

        tied = scenarios["tie"]
        self.assertTrue(tied["cancellation"])
        self.assertTrue(tied["timeout"])
        self.assertTrue(tied["tie_resolved_to_cancellation"])
        self.assertEqual(tied["terminal"], "cancelled-rollback-incomplete")
        self.assertEqual(tied["failure"], "startup-cancelled")

        checks = self.read("run_checks.m")
        for marker in (
            "tiedNoQuiescence = model",
            "cancelled-rollback-incomplete",
            "all(isnan(tiedNoQuiescence.shutdownFinalState))",
        ):
            self.assertIn(marker, checks)

    def test_independent_oracle_broken_assessment_preserves_factual_trace(self):
        for startup_position, shutdown_position in ((1, 6), (5, 1), (1, 1)):
            with self.subTest(startup=startup_position, shutdown=shutdown_position):
                strict = reference_sequence(
                    startup_enable_position=startup_position,
                    shutdown_power_position=shutdown_position,
                )
                broken = reference_sequence(
                    startup_enable_position=startup_position,
                    shutdown_power_position=shutdown_position,
                    assessment_mode="final-state-only",
                )
                assert_oracle_invariants(self, strict)
                assert_oracle_invariants(self, broken)
                for factual_key in (
                    "startup_actions",
                    "shutdown_actions",
                    "startup_pre",
                    "startup_post",
                    "startup_step",
                    "startup_trace",
                    "shutdown_pre",
                    "shutdown_post",
                    "shutdown_step",
                    "shutdown_trace",
                    "startup_final_running",
                    "shutdown_final_safe_off",
                    "strict_accepted",
                    "failure",
                ):
                    self.assertEqual(strict[factual_key], broken[factual_key])
                self.assertFalse(strict["reported_accepted"])
                self.assertTrue(broken["snapshot_accepted"])
                self.assertTrue(broken["reported_accepted"])
                self.assertTrue(broken["false_approval"])
                self.assertFalse(broken["decision_correct"])
                self.assertEqual(
                    broken["reporting_failure"],
                    "final-state-only-false-approval",
                )

        valid = reference_sequence(assessment_mode="final-state-only")
        invalid_contract = reference_sequence(
            p08_conformant=False,
            p08_eligible=False,
            assessment_mode="final-state-only",
        )
        self.assertTrue(valid["strict_accepted"])
        self.assertTrue(valid["reported_accepted"])
        self.assertFalse(valid["false_approval"])
        self.assertFalse(invalid_contract["snapshot_accepted"])
        self.assertFalse(invalid_contract["reported_accepted"])

    def test_every_supported_terminal_is_behaviorally_reachable(self):
        scenarios = [
            reference_sequence(),
            reference_sequence(startup_enable_position=1),
            reference_sequence(event_mode="cancellation"),
            reference_sequence(event_mode="timeout"),
            reference_sequence(
                startup_enable_position=1,
                fault_mode="actuator-stuck-on",
                event_mode="cancellation",
            ),
            reference_sequence(
                fault_mode="quiescence-not-confirmed",
                event_mode="timeout",
            ),
        ]
        self.assertEqual(
            {scenario["terminal"] for scenario in scenarios},
            {
                "completed-safe-off",
                "completed-with-hazard",
                "cancelled-safe-hold",
                "timed-out-safe-hold",
                "cancelled-rollback-incomplete",
                "timed-out-rollback-incomplete",
            },
        )

    def test_experiment_has_ordered_baseline_two_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sweep_sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sweep_sections), 2)
        for marker in (
            "baseline = model(5,6,true,true",
            "startupPositionSweep = 1:5",
            "shutdownPositionSweep = 1:6",
            "isequal(startupMissingByPosition,[3 3 2 1 0])",
            "isequal(shutdownMissingByPosition,[5 4 3 2 1 0])",
            "contractInvalid",
            "qualityWithheld",
            "actuatorStuck",
            "quiescenceMissing",
            "cancelled",
            "timedOut",
            "cancelledStuck",
            "timedOutNoQuiescence",
            "cancelled-rollback-incomplete",
            "timed-out-rollback-incomplete",
            "rollbackFailureMode",
            "cancellation-timeout-tie",
            "rollbackSafeHold",
            "strictBroken",
            "final-state-only",
            "broken.falseApproval",
            "isequaln(recovered,baseline)",
        ):
            self.assertIn(marker, experiment)
        self.assertLess(
            experiment.index("Mechanism after lever 1"), experiment.index("%% Sweep 2")
        )
        self.assertLess(
            experiment.index("Mechanism after lever 2"), experiment.index("%% Negative cases")
        )
        self.assertGreaterEqual(experiment.count("figure("), 5)
        for unit in (
            "action index (-)",
            "prerequisites (count)",
            "Boolean -",
            "state (Boolean -)",
        ):
            self.assertIn(unit, experiment)
        self.assertIn("No milliseconds", experiment)
        self.assertIn("not elapsed time", experiment)

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertGreaterEqual(interactive.count("uispinner"), 2)
        self.assertGreaterEqual(interactive.count("uicheckbox"), 2)
        self.assertGreaterEqual(interactive.count("uidropdown"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 7)
        self.assertIn("'Limits',[1 5]", interactive)
        self.assertIn("'Limits',[1 6]", interactive)
        self.assertIn("faultMode.ItemsData", interactive)
        self.assertIn("eventMode.ItemsData", interactive)
        self.assertIn("assessmentMode.ItemsData", interactive)
        self.assertIn("cancellation-timeout-tie", interactive)
        self.assertIn("final-state-only", interactive)
        self.assertIn("resetBaseline", interactive)
        for marker in (
            "startupPosition.Value = 5",
            "shutdownPosition.Value = 6",
            "p08Conformance.Value = true",
            "p08Eligibility.Value = true",
            "faultMode.Value = 'none'",
            "eventMode.Value = 'none'",
            "assessmentMode.Value = 'strict-order'",
        ):
            self.assertIn(marker, interactive)
        self.assertIn("Observed fact (Boolean -)", interactive)
        self.assertIn("false approval", interactive)
        self.assertIn("rollback failure", interactive)
        self.assertIn("not measured time", interactive)

    def test_checks_cover_malformed_limits_events_recovery_and_resources(self):
        checks = self.read("run_checks.m")
        for marker in (
            "expectedStartupActions",
            "expectedShutdownActions",
            "expectedRollbackActions",
            "expectedStateNames",
            "expectedStartupTrace",
            "expectedShutdownTrace",
            "expectedStartupMissing = [3 3 2 1 0]",
            "expectedShutdownMissing = [5 4 3 2 1 0]",
            "startupMinimum",
            "startupJustBeforeValid",
            "startupValidLimit",
            "shutdownMinimum",
            "shutdownJustBeforeValid",
            "shutdownValidLimit",
            "contractInvalid",
            "inputWithheld",
            "actuatorStuck",
            "quiescenceMissing",
            "cancelled",
            "timedOut",
            "tied",
            "tiedNoQuiescence",
            "timeoutBeforeContract",
            "eventAfterEarlyEnable",
            "cancelledStuck",
            "timedOutNoQuiescence",
            "cancelled-rollback-incomplete",
            "timed-out-rollback-incomplete",
            "rollbackFailureMode",
            "expectedEvaluatedBeforeEvent",
            "expectedRollbackTrace",
            "brokenScenarios",
            "brokenBaseline",
            "brokenContract",
            "string(' NONE ')",
            "P09:InvalidStartupEnablePosition",
            "P09:InvalidShutdownPowerOffPosition",
            "P09:InvalidP08Conformance",
            "P09:InvalidP08Eligibility",
            "P09:InconsistentP08Facts",
            "P09:InvalidFaultMode",
            "P09:InvalidEventMode",
            "P09:InvalidAssessmentMode",
            "afterMalformed",
            "afterCancellation",
            "afterTimeout",
            "afterBroken",
            "assertSequenceInvariant",
            "P09 checks passed",
        ):
            self.assertIn(marker, checks)

    def test_lesson_is_concept_first_compounds_and_preserves_boundaries(self):
        combined = "\n".join(
            self.read(name)
            for name in ("README.md", "lesson.m", "lesson.md", "walkthrough.md", "checks.md")
        )
        self.assertGreaterEqual(combined.count(QUESTION), 3)
        for marker in (
            "P08",
            "P10",
            "P11",
            "P12",
            "P13",
            "P18",
            "input",
            "observable",
            "failure",
            "startup",
            "shutdown",
            "precondition",
            "postcondition",
            "actuator",
            "quiescence",
            "cancellation",
            "timeout",
            "rollback",
            "recovery",
            "interpretation",
            "teach-back",
        ):
            self.assertIn(marker.lower(), combined.lower())
        flattened = re.sub(r"\s+", " ", combined)
        self.assertIn("P09 does not invoke P08", flattened)
        self.assertIn("Action position is a dimensionless index", flattened)
        self.assertIn("do not establish physical equipment safety", flattened)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_p08_compatibility_is_consumed_without_rewriting_prerequisite(self):
        p08_model = (
            ROOT / "modules/08-write-an-interface-control-contract/model.m"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            p08_model,
            r"function out = model\(sourceAngleDeg,payloadWordCount,senderVersion,",
        )
        self.assertIn("contractConformant", p08_model)
        self.assertIn("contractInputEligible", p08_model)
        combined = "\n".join(
            self.read(name) for name in ("README.md", "lesson.m", "lesson.md", "checks.md")
        )
        for marker in (
            "p08ContractConformant",
            "p08InputEligible",
            "P09 does not invoke P08",
            "latency, jitter, or distributed synchronization",
        ):
            self.assertIn(marker, combined)
        self.assertNotIn("run_module_checks", self.read("model.m"))

    def test_rollback_fixture_recovers_persisted_p09_to_p08_without_erasure(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 9:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            retained_note = "P09 startup/shutdown teach-back retained"
            (state_dir / "progress.json").write_text(
                json.dumps(
                    {
                        "current": "P09",
                        "completed": {"P09": True},
                        "notes": {"P09": retained_note},
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
            self.assertIn("P08 — Write an Interface Control Contract", recovered.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("24 total, 8 implemented, 0 completed", status.stdout)
            self.assertEqual(listing.returncode, 0, listing.stderr)
            p09_line = next(line for line in listing.stdout.splitlines() if " P09 " in line)
            self.assertTrue(p09_line.startswith("○ P09"), p09_line)
            self.assertNotIn("✓ P09", listing.stdout)
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P08")
            self.assertTrue(state["completed"]["P09"])
            self.assertEqual(state["notes"]["P09"], retained_note)

    def test_retained_evidence_has_required_sections_and_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P09-*.md"))
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
