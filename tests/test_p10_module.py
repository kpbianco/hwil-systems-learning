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
P10 = ROOT / "modules/10-model-system-states-and-transitions"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you model "
    "System States and Transitions?"
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
STATE_NAMES = ["OFF", "STANDBY", "READY", "ACTIVE", "FAULT", "SAFE-HOLD"]
OFF, STANDBY, READY, ACTIVE, FAULT, SAFE_HOLD = range(1, 7)
TRANSITION_COUNT = 13
EVENT_CHECKPOINT = 6
ROLLBACK_EVENT_NAMES = [
    "enter-safe-hold",
    "clear-transition-requests",
    "return-off-after-p09-proof",
]
TRANSITION_INPUT_NAMES = [
    "enter-standby-request",
    "readiness-evidence",
    "activate-request",
    "operate",
    "feedback-loss",
    "reset-request",
    "recovery-evidence",
    "stop-request",
    "off-request",
]
ALLOWED_TRANSITIONS = {
    OFF: {OFF, STANDBY},
    STANDBY: {STANDBY, READY, SAFE_HOLD},
    READY: {READY, ACTIVE, SAFE_HOLD},
    ACTIVE: {ACTIVE, FAULT, SAFE_HOLD},
    FAULT: {READY, FAULT, SAFE_HOLD},
    SAFE_HOLD: {OFF, SAFE_HOLD},
}


def one_hot(state_id: int) -> list[int]:
    return [int(index == state_id) for index in range(1, len(STATE_NAMES) + 1)]


def _validate_count(value: int, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value != round(value)
        or not 1 <= value <= 4
    ):
        raise ValueError(f"{name} must be an integer from 1 through 4")
    return int(value)


def _validate_bool(value: bool, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value in (0, 1)
    ):
        return bool(value)
    raise ValueError(f"{name} must be Boolean or numeric zero/one")


def _validate_choice(value: str, allowed: set[str], name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"unsupported {name}")
    return normalized


def reference_state_machine(
    readiness_confirmations: int = 2,
    recovery_confirmations: int = 2,
    p09_startup_proof: bool = True,
    p09_safe_off_proof: bool = True,
    scenario_mode: str = "nominal",
    event_mode: str = "none",
    arbitration_mode: str = "guarded-priority",
) -> dict[str, object]:
    """Independent Python oracle for P10's fixed, bounded transition lesson."""
    readiness_confirmations = _validate_count(
        readiness_confirmations, "readiness_confirmations"
    )
    recovery_confirmations = _validate_count(
        recovery_confirmations, "recovery_confirmations"
    )
    p09_startup_proof = _validate_bool(p09_startup_proof, "p09_startup_proof")
    p09_safe_off_proof = _validate_bool(
        p09_safe_off_proof, "p09_safe_off_proof"
    )
    scenario_mode = _validate_choice(
        scenario_mode,
        {
            "nominal",
            "recoverable-feedback-loss",
            "fault-reset-conflict",
            "state-stuck-active",
            "premature-activation",
        },
        "scenario_mode",
    )
    event_mode = _validate_choice(
        event_mode,
        {"none", "cancellation", "timeout", "cancellation-timeout-tie"},
        "event_mode",
    )
    arbitration_mode = _validate_choice(
        arbitration_mode,
        {"guarded-priority", "last-request-wins"},
        "arbitration_mode",
    )

    event_names = [
        "enter-standby-request",
        "readiness-evidence",
        "readiness-evidence",
        "readiness-evidence",
        "readiness-evidence",
        "activate-request",
        "operate",
        "operate",
        "operate",
        "operate",
        "operate",
        "stop-request",
        "off-request",
    ]
    if scenario_mode == "premature-activation":
        event_names[1] = "activate-request"
    elif scenario_mode == "recoverable-feedback-loss":
        event_names[6] = "feedback-loss"
        event_names[7:11] = ["recovery-evidence"] * 4
    elif scenario_mode == "fault-reset-conflict":
        event_names[6] = "feedback-loss+reset"
        event_names[7:11] = ["recovery-evidence"] * 4
    elif scenario_mode == "state-stuck-active":
        event_names[6] = "feedback-loss"

    transition_input_matrix = []
    for event_name in event_names:
        active_inputs = [False] * len(TRANSITION_INPUT_NAMES)
        if event_name == "feedback-loss+reset":
            active_inputs[TRANSITION_INPUT_NAMES.index("feedback-loss")] = True
            active_inputs[TRANSITION_INPUT_NAMES.index("reset-request")] = True
        else:
            active_inputs[TRANSITION_INPUT_NAMES.index(event_name)] = True
        transition_input_matrix.append(active_inputs)
    transition_input_count = [sum(row) for row in transition_input_matrix]
    transition_input_conflict = [count > 1 for count in transition_input_count]

    cancellation_requested = event_mode in {
        "cancellation",
        "cancellation-timeout-tie",
    }
    timeout_requested = event_mode in {"timeout", "cancellation-timeout-tie"}
    event_requested = cancellation_requested or timeout_requested
    observed_interruption_name = "none"
    preempted_transition_input = "none"
    cancellation_observed = False
    timeout_observed = False
    event_observed = False
    tie_resolved_to_cancellation = False

    transition_evaluated = [False] * TRANSITION_COUNT
    source_state_ids = [math.nan] * TRANSITION_COUNT
    strict_requested_state_ids = [math.nan] * TRANSITION_COUNT
    reported_requested_state_ids = [math.nan] * TRANSITION_COUNT
    observed_state_ids = [math.nan] * TRANSITION_COUNT
    transition_table_allowed = [False] * TRANSITION_COUNT
    reported_transition_table_allowed = [False] * TRANSITION_COUNT
    strict_guard_pass = [False] * TRANSITION_COUNT
    reported_guard_pass = [False] * TRANSITION_COUNT
    strict_postcondition_pass = [False] * TRANSITION_COUNT
    reported_postcondition_pass = [False] * TRANSITION_COUNT
    strict_transition_pass = [False] * TRANSITION_COUNT
    reported_transition_pass = [False] * TRANSITION_COUNT
    policy_step_accepted = [False] * TRANSITION_COUNT
    transition_hazard = [False] * TRANSITION_COUNT
    priority_violation = [False] * TRANSITION_COUNT
    guard_bypassed = [False] * TRANSITION_COUNT
    strict_selected_inputs = [""] * TRANSITION_COUNT
    reported_selected_inputs = [""] * TRANSITION_COUNT
    state_id_trace = [math.nan] * TRANSITION_COUNT
    state_occupancy_trace = [
        [math.nan] * len(STATE_NAMES) for _ in range(TRANSITION_COUNT)
    ]
    readiness_count_trace = [math.nan] * TRANSITION_COUNT
    recovery_count_trace = [math.nan] * TRANSITION_COUNT

    state_id = OFF
    readiness_count = 0
    recovery_count = 0
    readiness_qualified_step = math.nan
    recovery_qualified_step = math.nan
    sequence_halted = False

    for index, event_name in enumerate(event_names):
        one_based_step = index + 1
        if sequence_halted:
            break
        if event_requested and one_based_step == EVENT_CHECKPOINT:
            event_observed = True
            cancellation_observed = cancellation_requested
            timeout_observed = timeout_requested
            tie_resolved_to_cancellation = (
                cancellation_observed and timeout_observed
            )
            observed_interruption_name = event_mode
            preempted_transition_input = event_name
            break

        transition_evaluated[index] = True
        source = state_id
        strict_target = source
        reported_target = source
        guard_condition = False
        broken_conflict_accepted = False
        strict_selection = event_name
        reported_selection = event_name

        if event_name == "enter-standby-request":
            strict_target = STANDBY
            reported_target = strict_target
            guard_condition = source == OFF and p09_startup_proof
        elif event_name == "readiness-evidence":
            if source == STANDBY:
                readiness_count += 1
                if readiness_count >= readiness_confirmations:
                    strict_target = READY
                    if math.isnan(readiness_qualified_step):
                        readiness_qualified_step = one_based_step
                else:
                    strict_target = STANDBY
                guard_condition = True
            elif source == READY:
                strict_target = READY
                guard_condition = True
            reported_target = strict_target
        elif event_name == "activate-request":
            strict_target = ACTIVE
            reported_target = strict_target
            guard_condition = source == READY
        elif event_name == "operate":
            strict_target = ACTIVE
            reported_target = strict_target
            guard_condition = source == ACTIVE
        elif event_name == "feedback-loss":
            strict_target = FAULT
            reported_target = strict_target
            guard_condition = source == ACTIVE
        elif event_name == "feedback-loss+reset":
            strict_target = FAULT
            guard_condition = source == ACTIVE
            strict_selection = "feedback-loss"
            if arbitration_mode == "last-request-wins":
                reported_target = READY
                reported_selection = "reset-request"
                broken_conflict_accepted = source == ACTIVE
            else:
                reported_target = strict_target
                reported_selection = strict_selection
        elif event_name == "recovery-evidence":
            if source == FAULT:
                recovery_count += 1
                if recovery_count >= recovery_confirmations:
                    strict_target = READY
                    if math.isnan(recovery_qualified_step):
                        recovery_qualified_step = one_based_step
                else:
                    strict_target = FAULT
                guard_condition = True
            elif source == READY:
                strict_target = READY
                guard_condition = True
            reported_target = strict_target
        elif event_name == "stop-request":
            strict_target = SAFE_HOLD
            reported_target = strict_target
            guard_condition = source in {ACTIVE, READY}
        elif event_name == "off-request":
            strict_target = OFF
            reported_target = strict_target
            guard_condition = source == SAFE_HOLD and p09_safe_off_proof
        else:  # pragma: no cover - fixed event inventory
            raise AssertionError(event_name)

        strict_table = strict_target in ALLOWED_TRANSITIONS[source]
        reported_table = reported_target in ALLOWED_TRANSITIONS[source]
        strict_guard = guard_condition
        if broken_conflict_accepted:
            reported_guard = False
            policy_allows_transition = True
            priority_was_violated = True
        else:
            reported_guard = strict_guard
            policy_allows_transition = strict_table and strict_guard
            priority_was_violated = False

        next_state = source
        if policy_allows_transition:
            next_state = reported_target
        if (
            scenario_mode == "state-stuck-active"
            and event_name == "feedback-loss"
            and source == ACTIVE
        ):
            next_state = ACTIVE
        state_id = next_state
        strict_postcondition = state_id == strict_target
        reported_postcondition = state_id == reported_target

        source_state_ids[index] = source
        strict_requested_state_ids[index] = strict_target
        reported_requested_state_ids[index] = reported_target
        observed_state_ids[index] = state_id
        transition_table_allowed[index] = strict_table
        reported_transition_table_allowed[index] = reported_table
        strict_guard_pass[index] = strict_guard
        reported_guard_pass[index] = reported_guard
        strict_postcondition_pass[index] = strict_postcondition
        reported_postcondition_pass[index] = reported_postcondition
        strict_transition_pass[index] = (
            strict_table and strict_guard and strict_postcondition
        )
        reported_transition_pass[index] = (
            reported_table and reported_guard and reported_postcondition
        )
        policy_step_accepted[index] = (
            policy_allows_transition and reported_postcondition
        )
        transition_hazard[index] = not strict_transition_pass[index]
        priority_violation[index] = priority_was_violated
        guard_bypassed[index] = broken_conflict_accepted
        strict_selected_inputs[index] = strict_selection
        reported_selected_inputs[index] = reported_selection
        state_id_trace[index] = state_id
        state_occupancy_trace[index] = one_hot(state_id)
        readiness_count_trace[index] = readiness_count
        recovery_count_trace[index] = recovery_count

        if not policy_step_accepted[index]:
            sequence_halted = True

    sequence_completed = all(transition_evaluated)
    sequence_final_state_id = state_id if sequence_completed else math.nan
    strict_accepted = (
        sequence_completed and all(strict_transition_pass) and state_id == OFF
    )
    reported_accepted = (
        sequence_completed and all(policy_step_accepted) and state_id == OFF
    )
    false_approval = sequence_completed and reported_accepted and not strict_accepted
    decision_correct = sequence_completed and reported_accepted == strict_accepted

    rollback_executed = [False] * len(ROLLBACK_EVENT_NAMES)
    rollback_source_ids = [math.nan] * len(ROLLBACK_EVENT_NAMES)
    rollback_requested_ids = [math.nan] * len(ROLLBACK_EVENT_NAMES)
    rollback_observed_ids = [math.nan] * len(ROLLBACK_EVENT_NAMES)
    rollback_guard_pass = [False] * len(ROLLBACK_EVENT_NAMES)
    rollback_table_allowed = [False] * len(ROLLBACK_EVENT_NAMES)
    rollback_postcondition_pass = [False] * len(ROLLBACK_EVENT_NAMES)
    rollback_transition_pass = [False] * len(ROLLBACK_EVENT_NAMES)
    rollback_hazard = [False] * len(ROLLBACK_EVENT_NAMES)
    rollback_state_trace = [
        [math.nan] * len(STATE_NAMES) for _ in ROLLBACK_EVENT_NAMES
    ]
    rollback_performed = False
    rollback_complete = False
    rollback_final_state_id = math.nan

    if event_observed:
        rollback_performed = True
        rollback_state_id = state_id
        for index, rollback_event in enumerate(ROLLBACK_EVENT_NAMES):
            rollback_executed[index] = True
            source = rollback_state_id
            if rollback_event == "enter-safe-hold":
                target = SAFE_HOLD
                guard = source in {STANDBY, READY, ACTIVE, FAULT}
            elif rollback_event == "clear-transition-requests":
                target = SAFE_HOLD
                guard = source == SAFE_HOLD
            elif rollback_event == "return-off-after-p09-proof":
                target = OFF
                guard = source == SAFE_HOLD and p09_safe_off_proof
            else:  # pragma: no cover - fixed rollback inventory
                raise AssertionError(rollback_event)
            table_allowed = target in ALLOWED_TRANSITIONS[source]
            if table_allowed and guard:
                rollback_state_id = target
            postcondition = rollback_state_id == target
            rollback_source_ids[index] = source
            rollback_requested_ids[index] = target
            rollback_observed_ids[index] = rollback_state_id
            rollback_guard_pass[index] = guard
            rollback_table_allowed[index] = table_allowed
            rollback_postcondition_pass[index] = postcondition
            rollback_transition_pass[index] = table_allowed and guard and postcondition
            rollback_hazard[index] = not rollback_transition_pass[index]
            rollback_state_trace[index] = one_hot(rollback_state_id)
        rollback_complete = all(rollback_transition_pass) and rollback_state_id == OFF
        rollback_final_state_id = rollback_state_id

    state_observation_count = [
        sum(evaluated and observed == state for evaluated, observed in zip(
            transition_evaluated, state_id_trace
        ))
        for state in range(1, len(STATE_NAMES) + 1)
    ]
    state_change_count = sum(
        evaluated and source != observed
        for evaluated, source, observed in zip(
            transition_evaluated, source_state_ids, observed_state_ids
        )
    )
    transition_violation_count = sum(
        evaluated and not passed
        for evaluated, passed in zip(transition_evaluated, strict_transition_pass)
    )
    reported_violation_count = sum(
        evaluated and not passed
        for evaluated, passed in zip(transition_evaluated, reported_transition_pass)
    )
    policy_violation_count = sum(
        evaluated and not passed
        for evaluated, passed in zip(transition_evaluated, policy_step_accepted)
    )
    rollback_violation_count = sum(
        executed and not passed
        for executed, passed in zip(rollback_executed, rollback_transition_pass)
    )
    priority_violation_count = sum(
        evaluated and violated
        for evaluated, violated in zip(transition_evaluated, priority_violation)
    )
    first_violations = [
        index + 1
        for index, (evaluated, passed) in enumerate(
            zip(transition_evaluated, strict_transition_pass)
        )
        if evaluated and not passed
    ]
    first_violation_step = first_violations[0] if first_violations else math.nan

    if cancellation_observed and rollback_complete:
        terminal = "cancelled-rollback-complete"
    elif cancellation_observed:
        terminal = "cancelled-rollback-incomplete"
    elif timeout_observed and rollback_complete:
        terminal = "timed-out-rollback-complete"
    elif timeout_observed:
        terminal = "timed-out-rollback-incomplete"
    elif strict_accepted:
        terminal = "completed-off"
    elif false_approval:
        terminal = "completed-false-approval"
    else:
        terminal = "rejected-transition"

    if cancellation_observed:
        failure = "state-transition-cancelled"
    elif timeout_observed:
        failure = "state-transition-timeout"
    elif not p09_startup_proof:
        failure = "p09-startup-proof-unavailable"
    elif scenario_mode == "premature-activation" and first_violations:
        failure = "activation-before-ready"
    elif scenario_mode == "state-stuck-active" and first_violations:
        failure = "state-postcondition-failed"
    elif priority_violation_count:
        failure = "fault-priority-bypassed"
    elif not p09_safe_off_proof:
        failure = "p09-safe-off-proof-unavailable"
    elif transition_violation_count:
        failure = "transition-guard-rejected"
    else:
        failure = "none"

    return {
        "state_names": STATE_NAMES.copy(),
        "event_names": event_names,
        "rollback_event_names": ROLLBACK_EVENT_NAMES.copy(),
        "transition_input_names": TRANSITION_INPUT_NAMES.copy(),
        "transition_input_matrix": transition_input_matrix,
        "transition_input_count": transition_input_count,
        "transition_input_conflict": transition_input_conflict,
        "transition_evaluated": transition_evaluated,
        "source_state_ids": source_state_ids,
        "strict_requested_state_ids": strict_requested_state_ids,
        "reported_requested_state_ids": reported_requested_state_ids,
        "observed_state_ids": observed_state_ids,
        "transition_table_allowed": transition_table_allowed,
        "reported_transition_table_allowed": reported_transition_table_allowed,
        "strict_guard_pass": strict_guard_pass,
        "reported_guard_pass": reported_guard_pass,
        "strict_postcondition_pass": strict_postcondition_pass,
        "reported_postcondition_pass": reported_postcondition_pass,
        "strict_transition_pass": strict_transition_pass,
        "reported_transition_pass": reported_transition_pass,
        "policy_step_accepted": policy_step_accepted,
        "transition_hazard": transition_hazard,
        "priority_violation": priority_violation,
        "guard_bypassed": guard_bypassed,
        "strict_selected_inputs": strict_selected_inputs,
        "reported_selected_inputs": reported_selected_inputs,
        "state_id_trace": state_id_trace,
        "state_occupancy_trace": state_occupancy_trace,
        "readiness_count_trace": readiness_count_trace,
        "recovery_count_trace": recovery_count_trace,
        "readiness_count": readiness_count,
        "recovery_count": recovery_count,
        "readiness_qualified_step": readiness_qualified_step,
        "recovery_qualified_step": recovery_qualified_step,
        "state_observation_count": state_observation_count,
        "state_change_count": state_change_count,
        "sequence_completed": sequence_completed,
        "sequence_halted": sequence_halted,
        "sequence_final_state_id": sequence_final_state_id,
        "strict_accepted": strict_accepted,
        "reported_accepted": reported_accepted,
        "false_approval": false_approval,
        "decision_correct": decision_correct,
        "cancellation_requested": cancellation_requested,
        "timeout_requested": timeout_requested,
        "event_requested": event_requested,
        "cancellation_observed": cancellation_observed,
        "timeout_observed": timeout_observed,
        "event_observed": event_observed,
        "observed_interruption_name": observed_interruption_name,
        "preempted_transition_input": preempted_transition_input,
        "tie_resolved_to_cancellation": tie_resolved_to_cancellation,
        "rollback_executed": rollback_executed,
        "rollback_source_ids": rollback_source_ids,
        "rollback_requested_ids": rollback_requested_ids,
        "rollback_observed_ids": rollback_observed_ids,
        "rollback_guard_pass": rollback_guard_pass,
        "rollback_table_allowed": rollback_table_allowed,
        "rollback_postcondition_pass": rollback_postcondition_pass,
        "rollback_transition_pass": rollback_transition_pass,
        "rollback_hazard": rollback_hazard,
        "rollback_state_trace": rollback_state_trace,
        "rollback_performed": rollback_performed,
        "rollback_complete": rollback_complete,
        "rollback_final_state_id": rollback_final_state_id,
        "transition_violation_count": transition_violation_count,
        "reported_violation_count": reported_violation_count,
        "policy_violation_count": policy_violation_count,
        "rollback_violation_count": rollback_violation_count,
        "priority_violation_count": priority_violation_count,
        "total_violation_count": (
            transition_violation_count + rollback_violation_count
        ),
        "first_violation_step": first_violation_step,
        "terminal": terminal,
        "failure": failure,
        "reporting_failure": (
            "last-request-wins-false-approval" if false_approval else "none"
        ),
        "rollback_failure": (
            "p09-safe-off-proof-unavailable"
            if event_observed and not rollback_complete
            else "none"
        ),
        "terminal_outcome_handled": (
            sequence_completed or sequence_halted or event_observed
        ),
    }


def assert_oracle_invariants(test: unittest.TestCase, result: dict[str, object]) -> None:
    numeric_traces = (
        "source_state_ids",
        "strict_requested_state_ids",
        "reported_requested_state_ids",
        "observed_state_ids",
        "state_id_trace",
        "readiness_count_trace",
        "recovery_count_trace",
    )
    boolean_traces = (
        "transition_table_allowed",
        "reported_transition_table_allowed",
        "strict_guard_pass",
        "reported_guard_pass",
        "strict_postcondition_pass",
        "reported_postcondition_pass",
        "strict_transition_pass",
        "reported_transition_pass",
        "policy_step_accepted",
        "transition_hazard",
        "priority_violation",
        "guard_bypassed",
    )
    test.assertEqual(result["state_names"], STATE_NAMES)
    test.assertEqual(len(result["event_names"]), TRANSITION_COUNT)
    test.assertEqual(result["rollback_event_names"], ROLLBACK_EVENT_NAMES)
    test.assertEqual(result["transition_input_names"], TRANSITION_INPUT_NAMES)
    test.assertEqual(len(result["transition_input_matrix"]), TRANSITION_COUNT)
    test.assertTrue(
        all(
            len(row) == len(TRANSITION_INPUT_NAMES)
            for row in result["transition_input_matrix"]
        )
    )
    test.assertEqual(
        result["transition_input_count"],
        [sum(row) for row in result["transition_input_matrix"]],
    )
    test.assertEqual(
        result["transition_input_conflict"],
        [count > 1 for count in result["transition_input_count"]],
    )
    test.assertLessEqual(max(result["transition_input_count"]), 2)
    test.assertEqual(len(result["transition_evaluated"]), TRANSITION_COUNT)
    test.assertEqual(len(result["strict_selected_inputs"]), TRANSITION_COUNT)
    test.assertEqual(len(result["reported_selected_inputs"]), TRANSITION_COUNT)
    for name in (*numeric_traces, *boolean_traces):
        test.assertEqual(len(result[name]), TRANSITION_COUNT, name)
    test.assertEqual(len(result["state_occupancy_trace"]), TRANSITION_COUNT)
    test.assertTrue(
        all(len(row) == len(STATE_NAMES) for row in result["state_occupancy_trace"])
    )

    for index, evaluated in enumerate(result["transition_evaluated"]):
        if evaluated:
            test.assertTrue(result["strict_selected_inputs"][index])
            test.assertTrue(result["reported_selected_inputs"][index])
            for name in numeric_traces:
                test.assertTrue(math.isfinite(result[name][index]), (name, index))
            source = result["source_state_ids"][index]
            strict_target = result["strict_requested_state_ids"][index]
            reported_target = result["reported_requested_state_ids"][index]
            observed = result["observed_state_ids"][index]
            test.assertIn(source, range(1, len(STATE_NAMES) + 1))
            test.assertIn(strict_target, range(1, len(STATE_NAMES) + 1))
            test.assertIn(reported_target, range(1, len(STATE_NAMES) + 1))
            test.assertIn(observed, range(1, len(STATE_NAMES) + 1))
            test.assertEqual(
                result["transition_table_allowed"][index],
                strict_target in ALLOWED_TRANSITIONS[source],
            )
            test.assertEqual(
                result["reported_transition_table_allowed"][index],
                reported_target in ALLOWED_TRANSITIONS[source],
            )
            test.assertEqual(
                result["strict_postcondition_pass"][index],
                observed == strict_target,
            )
            test.assertEqual(
                result["reported_postcondition_pass"][index],
                observed == reported_target,
            )
            test.assertEqual(result["state_id_trace"][index], observed)
            test.assertEqual(result["state_occupancy_trace"][index], one_hot(observed))
        else:
            test.assertEqual(result["strict_selected_inputs"][index], "")
            test.assertEqual(result["reported_selected_inputs"][index], "")
            for name in numeric_traces:
                test.assertTrue(math.isnan(result[name][index]), (name, index))
            for name in boolean_traces:
                test.assertFalse(result[name][index], (name, index))
            test.assertTrue(
                all(math.isnan(value) for value in result["state_occupancy_trace"][index])
            )

    test.assertEqual(
        result["strict_transition_pass"],
        [
            allowed and guard and postcondition
            for allowed, guard, postcondition in zip(
                result["transition_table_allowed"],
                result["strict_guard_pass"],
                result["strict_postcondition_pass"],
            )
        ],
    )
    test.assertEqual(
        result["reported_transition_pass"],
        [
            allowed and guard and postcondition
            for allowed, guard, postcondition in zip(
                result["reported_transition_table_allowed"],
                result["reported_guard_pass"],
                result["reported_postcondition_pass"],
            )
        ],
    )
    test.assertEqual(
        result["transition_hazard"],
        [
            evaluated and not passed
            for evaluated, passed in zip(
                result["transition_evaluated"], result["strict_transition_pass"]
            )
        ],
    )
    test.assertEqual(
        result["strict_accepted"],
        result["sequence_completed"]
        and all(result["strict_transition_pass"])
        and result["sequence_final_state_id"] == OFF,
    )
    test.assertEqual(
        result["reported_accepted"],
        result["sequence_completed"]
        and all(result["policy_step_accepted"])
        and result["sequence_final_state_id"] == OFF,
    )
    test.assertEqual(
        result["false_approval"],
        result["sequence_completed"]
        and result["reported_accepted"]
        and not result["strict_accepted"],
    )
    test.assertEqual(
        result["decision_correct"],
        result["sequence_completed"]
        and result["reported_accepted"] == result["strict_accepted"],
    )
    test.assertEqual(
        result["transition_violation_count"],
        sum(
            evaluated and not passed
            for evaluated, passed in zip(
                result["transition_evaluated"], result["strict_transition_pass"]
            )
        ),
    )
    test.assertEqual(
        result["reported_violation_count"],
        sum(
            evaluated and not passed
            for evaluated, passed in zip(
                result["transition_evaluated"], result["reported_transition_pass"]
            )
        ),
    )
    test.assertEqual(
        result["policy_violation_count"],
        sum(
            evaluated and not passed
            for evaluated, passed in zip(
                result["transition_evaluated"], result["policy_step_accepted"]
            )
        ),
    )
    test.assertEqual(
        result["total_violation_count"],
        result["transition_violation_count"] + result["rollback_violation_count"],
    )
    test.assertEqual(
        sum(result["state_observation_count"]),
        sum(result["transition_evaluated"]),
    )
    test.assertEqual(
        result["event_observed"],
        result["cancellation_observed"] or result["timeout_observed"],
    )
    test.assertEqual(
        result["tie_resolved_to_cancellation"],
        result["cancellation_observed"] and result["timeout_observed"],
    )
    test.assertEqual(
        result["rollback_transition_pass"],
        [
            allowed and guard and postcondition
            for allowed, guard, postcondition in zip(
                result["rollback_table_allowed"],
                result["rollback_guard_pass"],
                result["rollback_postcondition_pass"],
            )
        ],
    )
    test.assertEqual(
        result["rollback_hazard"],
        [
            executed and not passed
            for executed, passed in zip(
                result["rollback_executed"], result["rollback_transition_pass"]
            )
        ],
    )
    if result["event_observed"]:
        test.assertTrue(result["rollback_performed"])
        test.assertNotEqual(result["observed_interruption_name"], "none")
        test.assertEqual(result["preempted_transition_input"], "activate-request")
        test.assertTrue(all(result["rollback_executed"]))
        test.assertTrue(all(result["rollback_table_allowed"]))
        test.assertEqual(len(result["rollback_state_trace"]), 3)
        test.assertTrue(
            all(
                math.isfinite(value)
                for row in result["rollback_state_trace"]
                for value in row
            )
        )
        test.assertEqual(
            result["rollback_complete"],
            all(result["rollback_transition_pass"])
            and result["rollback_final_state_id"] == OFF,
        )
        test.assertTrue(math.isnan(result["sequence_final_state_id"]))
    else:
        test.assertFalse(result["rollback_performed"])
        test.assertEqual(result["observed_interruption_name"], "none")
        test.assertEqual(result["preempted_transition_input"], "none")
        test.assertFalse(any(result["rollback_executed"]))
        test.assertFalse(any(result["rollback_table_allowed"]))
        test.assertFalse(any(result["rollback_guard_pass"]))
        test.assertFalse(any(result["rollback_postcondition_pass"]))
        test.assertFalse(any(result["rollback_transition_pass"]))
        test.assertFalse(any(result["rollback_hazard"]))
        test.assertTrue(
            all(
                math.isnan(value)
                for name in (
                    "rollback_source_ids",
                    "rollback_requested_ids",
                    "rollback_observed_ids",
                )
                for value in result[name]
            )
        )
        test.assertTrue(
            all(
                math.isnan(value)
                for row in result["rollback_state_trace"]
                for value in row
            )
        )
        test.assertFalse(result["rollback_complete"])
        test.assertTrue(math.isnan(result["rollback_final_state_id"]))
        test.assertEqual(result["rollback_failure"], "none")


class P10ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P10")

    def read(self, name: str) -> str:
        path = P10 / name
        self.assertTrue(path.is_file(), f"missing required P10 artifact: {path}")
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
                "number": 10,
                "id": "P10",
                "title": "Model System States and Transitions",
                "guiding_question": QUESTION,
                "phase": 3,
                "phase_title": "Sequencing and synchronization",
                "slug": "model-system-states-and-transitions",
                "folder": "modules/10-model-system-states-and-transitions",
                "implementation_batch": "P10",
                "prerequisites": ["P09"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P09"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P10.iterdir() if path.is_file()}
        )

    def test_owned_text_has_no_residue_and_exact_terminal_newline(self):
        owned_paths = [P10 / name for name in sorted(REQUIRED_ARTIFACTS)]
        owned_paths.append(Path(__file__))
        owned_paths.extend(sorted((ROOT / "docs/evidence").glob("P10-*.md")))
        for path in owned_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file(), f"missing owned text file: {path}")
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.endswith("\n"))
                self.assertFalse(content.endswith("\n\n"))
                if path.parent == P10:
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
            r"function out = model\(readinessConfirmations,recoveryConfirmations,\s*\.\.\.\s*p09StartupProof,p09SafeOffProof,",
        )
        for marker in (
            "minimumReadinessConfirmations = 1",
            "maximumReadinessConfirmations = 4",
            "minimumRecoveryConfirmations = 1",
            "maximumRecoveryConfirmations = 4",
            "transitionCount = 13",
            "stateCount = 6",
            "rollbackTransitionCount = 3",
            "eventCheckpointTransition = 6",
            "stateNames = {'OFF','STANDBY','READY','ACTIVE','FAULT','SAFE-HOLD'}",
        ):
            self.assertIn(marker, model)
        for marker in (
            "strictRequestedStateId",
            "reportedRequestedStateId",
            "observedStateId",
            "transitionTableAllowed",
            "reportedTransitionTableAllowed",
            "strictGuardPass",
            "reportedGuardPass",
            "strictPostconditionPass",
            "reportedPostconditionPass",
            "strictTransitionPass",
            "reportedTransitionPass",
            "policyStepAccepted",
            "priorityViolation",
            "guardBypassed",
            "strictSelectedInput",
            "reportedSelectedInput",
            "observedInterruptionName",
            "preemptedTransitionInput",
            "rollbackTransitionPass",
            "rollbackTransitionTableAllowed",
            "rollbackComplete",
            "terminalOutcomeHandled",
        ):
            self.assertIn(marker, model)
        for marker in (
            "transitionInputNames",
            "transitionInputMatrix",
            "transitionInputCount",
            "transitionInputConflict",
            "maximumSimultaneousTransitionInputs = 2",
            "stateObservationCount",
        ):
            self.assertIn(marker, model)
        for fragment in (
            "strictTransitionPass(k)=tableAllowed&&strictGuard&&strictPostcondition;",
            "reportedTransitionPass(k)=reportedTableAllowed&&reportedGuard&&reportedPostcondition;",
            "policyStepAccepted(k)=policyAllowsTransition&&reportedPostcondition;",
            "transitionHazard(k)=~strictTransitionPass(k);",
            "strictStateMachineAccepted=sequenceCompleted&&all(strictTransitionPass)&&stateId==offState;",
            "reportedStateMachineAccepted=sequenceCompleted&&all(policyStepAccepted)&&stateId==offState;",
            "falseApproval=sequenceCompleted&&reportedStateMachineAccepted&&~strictStateMachineAccepted;",
            "totalViolationCount=transitionViolationCount+rollbackViolationCount;",
            "normalized=double(value);",
            "normalized~=round(normalized)",
            "isfinite(value)&&(value==0||value==1)",
            "out.strictRequestedStateId=strictRequestedStateId;",
            "out.reportedRequestedStateId=reportedRequestedStateId;",
            "out.strictSelectedInput=strictSelectedInput;",
            "out.reportedSelectedInput=reportedSelectedInput;",
            "out.policyStepAccepted=policyStepAccepted;",
            "out.guardBypassed=guardBypassed;",
            "out.observedInterruptionName=observedInterruptionName;",
            "out.preemptedTransitionInput=preemptedTransitionInput;",
            "out.rollbackTransitionTableAllowed=rollbackTransitionTableAllowed;",
            "out.transitionInputNames=transitionInputNames;",
            "out.transitionInputMatrix=transitionInputMatrix;",
            "out.transitionInputCount=transitionInputCount;",
            "out.transitionInputConflict=transitionInputConflict;",
            "out.stateObservationCount=stateObservationCount;",
            "strictTarget=faultState;strictGuard=source==activeState;strictSelection='feedback-loss';",
            "reportedTarget=readyState;reportedSelection='reset-request';",
            "reportedGuard=false;policyAllowsTransition=true;priorityWasViolated=true;",
            "guardBypassed(k)=policyAllowsTransition&&(~reportedTableAllowed||~reportedGuard);",
            "rollbackTransitionPass(k)=tableAllowed&&guard&&postcondition;",
            "rollbackComplete=all(rollbackTransitionPass)&&rollbackStateId==offState;",
            "maximumSimultaneousTransitionInputs=2;",
            "out.maximumSimultaneousTransitionInputs=maximumSimultaneousTransitionInputs;",
            "elseifpriorityViolationCount>0failureMode='fault-priority-bypassed';",
        ):
            self.assertIn(fragment, compact)
        self.assertIn(
            "case'stop-request'strictTarget=safeHoldState;reportedTarget=strictTarget;",
            compact,
        )
        self.assertIn(
            "case'off-request'strictTarget=offState;reportedTarget=strictTarget;",
            compact,
        )
        for error_id in (
            "P10:InvalidReadinessConfirmations",
            "P10:InvalidRecoveryConfirmations",
            "P10:InvalidP09StartupProof",
            "P10:InvalidP09SafeOffProof",
            "P10:InvalidScenarioMode",
            "P10:InvalidEventMode",
            "P10:InvalidArbitrationMode",
            "p09-startup-proof-unavailable",
            "p09-safe-off-proof-unavailable",
            "cancelled-rollback-complete",
            "cancelled-rollback-incomplete",
            "timed-out-rollback-complete",
            "timed-out-rollback-incomplete",
            "completed-false-approval",
            "last-request-wins-false-approval",
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
            path.read_text(encoding="utf-8") for path in sorted(P10.glob("*.m"))
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
            "stateflow",
            "digraph(",
            "graph(",
            "timer(",
            "tic(",
            "toc(",
            "pause(",
        ):
            self.assertNotIn(opaque_or_external, all_matlab)
        self.assertNotIn("run_module_checks", model)

    def test_independent_oracle_baseline_exact_trace_and_metrics(self):
        baseline = reference_state_machine()
        assert_oracle_invariants(self, baseline)
        expected_trace = [
            STANDBY,
            STANDBY,
            READY,
            READY,
            READY,
            ACTIVE,
            ACTIVE,
            ACTIVE,
            ACTIVE,
            ACTIVE,
            ACTIVE,
            SAFE_HOLD,
            OFF,
        ]
        self.assertEqual(baseline["state_id_trace"], expected_trace)
        self.assertEqual(
            baseline["state_occupancy_trace"], [one_hot(state) for state in expected_trace]
        )
        self.assertEqual(baseline["state_observation_count"], [1, 2, 3, 6, 0, 1])
        self.assertEqual(baseline["state_change_count"], 5)
        self.assertEqual(baseline["readiness_count"], 2)
        self.assertEqual(baseline["readiness_qualified_step"], 3)
        self.assertEqual(baseline["recovery_count"], 0)
        self.assertTrue(math.isnan(baseline["recovery_qualified_step"]))
        self.assertTrue(all(baseline["strict_transition_pass"]))
        self.assertTrue(all(baseline["reported_transition_pass"]))
        self.assertTrue(baseline["strict_accepted"])
        self.assertTrue(baseline["reported_accepted"])
        self.assertTrue(baseline["decision_correct"])
        self.assertFalse(baseline["false_approval"])
        self.assertEqual(baseline["sequence_final_state_id"], OFF)
        self.assertEqual(baseline["terminal"], "completed-off")
        self.assertEqual(baseline["failure"], "none")
        self.assertTrue(baseline["terminal_outcome_handled"])

    def test_independent_oracle_readiness_sweep_and_limiting_cases(self):
        results = [
            reference_state_machine(readiness_confirmations=count)
            for count in range(1, 5)
        ]
        for result in results:
            assert_oracle_invariants(self, result)
            self.assertTrue(result["strict_accepted"])
        self.assertEqual(
            [result["readiness_qualified_step"] for result in results],
            [2, 3, 4, 5],
        )
        self.assertEqual(
            [result["state_observation_count"][STANDBY - 1] for result in results],
            [1, 2, 3, 4],
        )
        self.assertEqual(
            [result["state_observation_count"][READY - 1] for result in results],
            [4, 3, 2, 1],
        )
        self.assertEqual(
            [result["state_id_trace"][:5] for result in results],
            [
                [STANDBY, READY, READY, READY, READY],
                [STANDBY, STANDBY, READY, READY, READY],
                [STANDBY, STANDBY, STANDBY, READY, READY],
                [STANDBY, STANDBY, STANDBY, STANDBY, READY],
            ],
        )
        for invalid in (
            0,
            5,
            -1,
            True,
            1.5,
            math.nan,
            math.inf,
            2 + 1j,
            [2],
            "2",
            None,
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                reference_state_machine(readiness_confirmations=invalid)

    def test_independent_oracle_recovery_sweep_and_limiting_cases(self):
        results = [
            reference_state_machine(
                recovery_confirmations=count,
                scenario_mode="recoverable-feedback-loss",
            )
            for count in range(1, 5)
        ]
        for result in results:
            assert_oracle_invariants(self, result)
            self.assertTrue(result["strict_accepted"])
            self.assertEqual(result["failure"], "none")
        self.assertEqual(
            [result["recovery_qualified_step"] for result in results],
            [8, 9, 10, 11],
        )
        self.assertEqual(
            [result["state_observation_count"][FAULT - 1] for result in results],
            [1, 2, 3, 4],
        )
        default = results[1]
        self.assertEqual(
            default["state_id_trace"],
            [
                STANDBY,
                STANDBY,
                READY,
                READY,
                READY,
                ACTIVE,
                FAULT,
                FAULT,
                READY,
                READY,
                READY,
                SAFE_HOLD,
                OFF,
            ],
        )
        self.assertEqual(default["recovery_count"], 2)
        for invalid in (
            0,
            5,
            -1,
            False,
            2.5,
            math.nan,
            -math.inf,
            2 + 1j,
            [2],
            "2",
            None,
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                reference_state_machine(recovery_confirmations=invalid)

    def test_independent_oracle_negative_p09_proofs_are_not_weak_snapshots(self):
        startup_invalid = reference_state_machine(p09_startup_proof=False)
        safe_off_unavailable = reference_state_machine(p09_safe_off_proof=False)
        for result in (startup_invalid, safe_off_unavailable):
            assert_oracle_invariants(self, result)
            self.assertFalse(result["strict_accepted"])
            self.assertFalse(result["reported_accepted"])
            self.assertEqual(result["terminal"], "rejected-transition")

        self.assertEqual(startup_invalid["transition_evaluated"], [True] + [False] * 12)
        self.assertEqual(startup_invalid["source_state_ids"][0], OFF)
        self.assertEqual(startup_invalid["strict_requested_state_ids"][0], STANDBY)
        self.assertEqual(startup_invalid["observed_state_ids"][0], OFF)
        self.assertTrue(startup_invalid["transition_table_allowed"][0])
        self.assertFalse(startup_invalid["strict_guard_pass"][0])
        self.assertFalse(startup_invalid["strict_postcondition_pass"][0])
        self.assertEqual(startup_invalid["first_violation_step"], 1)
        self.assertEqual(startup_invalid["failure"], "p09-startup-proof-unavailable")

        self.assertEqual(safe_off_unavailable["transition_evaluated"], [True] * 13)
        self.assertEqual(safe_off_unavailable["source_state_ids"][12], SAFE_HOLD)
        self.assertEqual(safe_off_unavailable["strict_requested_state_ids"][12], OFF)
        self.assertEqual(safe_off_unavailable["observed_state_ids"][12], SAFE_HOLD)
        self.assertFalse(safe_off_unavailable["strict_guard_pass"][12])
        self.assertFalse(safe_off_unavailable["strict_postcondition_pass"][12])
        self.assertEqual(safe_off_unavailable["first_violation_step"], 13)
        self.assertEqual(
            safe_off_unavailable["failure"], "p09-safe-off-proof-unavailable"
        )

    def test_premature_activation_and_stuck_postcondition_halt_observation(self):
        premature = reference_state_machine(scenario_mode="premature-activation")
        stuck = reference_state_machine(scenario_mode="state-stuck-active")
        for result in (premature, stuck):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["sequence_halted"])
            self.assertFalse(result["sequence_completed"])
            self.assertTrue(result["terminal_outcome_handled"])
            self.assertEqual(result["terminal"], "rejected-transition")

        self.assertEqual(premature["transition_evaluated"], [True] * 2 + [False] * 11)
        self.assertEqual(premature["state_id_trace"][:2], [STANDBY] * 2)
        self.assertEqual(premature["source_state_ids"][1], STANDBY)
        self.assertEqual(premature["strict_requested_state_ids"][1], ACTIVE)
        self.assertEqual(premature["observed_state_ids"][1], STANDBY)
        self.assertFalse(premature["transition_table_allowed"][1])
        self.assertFalse(premature["strict_guard_pass"][1])
        self.assertFalse(premature["strict_postcondition_pass"][1])
        self.assertEqual(premature["first_violation_step"], 2)
        self.assertEqual(premature["failure"], "activation-before-ready")

        self.assertEqual(stuck["transition_evaluated"], [True] * 7 + [False] * 6)
        self.assertEqual(stuck["source_state_ids"][6], ACTIVE)
        self.assertEqual(stuck["strict_requested_state_ids"][6], FAULT)
        self.assertEqual(stuck["observed_state_ids"][6], ACTIVE)
        self.assertTrue(stuck["transition_table_allowed"][6])
        self.assertTrue(stuck["strict_guard_pass"][6])
        self.assertFalse(stuck["strict_postcondition_pass"][6])
        self.assertEqual(stuck["first_violation_step"], 7)
        self.assertEqual(stuck["failure"], "state-postcondition-failed")

    def test_cancellation_timeout_tie_complete_three_step_rollback(self):
        cancelled = reference_state_machine(event_mode="cancellation")
        timed_out = reference_state_machine(event_mode="timeout")
        tied = reference_state_machine(event_mode="cancellation-timeout-tie")
        for result in (cancelled, timed_out, tied):
            assert_oracle_invariants(self, result)
            self.assertEqual(result["transition_evaluated"], [True] * 5 + [False] * 8)
            self.assertTrue(result["event_observed"])
            self.assertTrue(result["rollback_performed"])
            self.assertTrue(result["rollback_complete"])
            self.assertEqual(result["rollback_source_ids"], [READY, SAFE_HOLD, SAFE_HOLD])
            self.assertEqual(result["rollback_requested_ids"], [SAFE_HOLD, SAFE_HOLD, OFF])
            self.assertEqual(result["rollback_observed_ids"], [SAFE_HOLD, SAFE_HOLD, OFF])
            self.assertTrue(all(result["rollback_transition_pass"]))
            self.assertEqual(
                result["rollback_state_trace"],
                [one_hot(SAFE_HOLD), one_hot(SAFE_HOLD), one_hot(OFF)],
            )
            self.assertEqual(result["rollback_violation_count"], 0)
            self.assertEqual(result["total_violation_count"], 0)
            self.assertTrue(math.isnan(result["first_violation_step"]))
            self.assertTrue(result["terminal_outcome_handled"])

        self.assertTrue(cancelled["cancellation_observed"])
        self.assertFalse(cancelled["timeout_observed"])
        self.assertEqual(cancelled["observed_interruption_name"], "cancellation")
        self.assertEqual(cancelled["preempted_transition_input"], "activate-request")
        self.assertEqual(cancelled["terminal"], "cancelled-rollback-complete")
        self.assertEqual(cancelled["failure"], "state-transition-cancelled")
        self.assertFalse(timed_out["cancellation_observed"])
        self.assertTrue(timed_out["timeout_observed"])
        self.assertEqual(timed_out["observed_interruption_name"], "timeout")
        self.assertEqual(timed_out["terminal"], "timed-out-rollback-complete")
        self.assertEqual(timed_out["failure"], "state-transition-timeout")
        self.assertTrue(tied["cancellation_observed"])
        self.assertTrue(tied["timeout_observed"])
        self.assertTrue(tied["tie_resolved_to_cancellation"])
        self.assertEqual(
            tied["observed_interruption_name"], "cancellation-timeout-tie"
        )
        self.assertEqual(tied["terminal"], "cancelled-rollback-complete")
        self.assertEqual(tied["failure"], "state-transition-cancelled")

    def test_incomplete_rollback_is_visible_for_cancel_and_timeout(self):
        cancelled = reference_state_machine(
            p09_safe_off_proof=False, event_mode="cancellation"
        )
        timed_out = reference_state_machine(
            p09_safe_off_proof=False, event_mode="timeout"
        )
        tied = reference_state_machine(
            p09_safe_off_proof=False, event_mode="cancellation-timeout-tie"
        )
        for result in (cancelled, timed_out, tied):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["rollback_performed"])
            self.assertFalse(result["rollback_complete"])
            self.assertEqual(
                result["rollback_observed_ids"], [SAFE_HOLD, SAFE_HOLD, SAFE_HOLD]
            )
            self.assertEqual(result["rollback_transition_pass"], [True, True, False])
            self.assertEqual(result["rollback_hazard"], [False, False, True])
            self.assertEqual(result["rollback_final_state_id"], SAFE_HOLD)
            self.assertEqual(result["rollback_violation_count"], 1)
            self.assertEqual(result["total_violation_count"], 1)
            self.assertEqual(
                result["rollback_failure"], "p09-safe-off-proof-unavailable"
            )
        self.assertEqual(cancelled["terminal"], "cancelled-rollback-incomplete")
        self.assertEqual(timed_out["terminal"], "timed-out-rollback-incomplete")
        self.assertEqual(tied["terminal"], "cancelled-rollback-incomplete")

    def test_event_and_output_isolation_survive_earlier_halt(self):
        halted = reference_state_machine(
            p09_startup_proof=False, event_mode="cancellation-timeout-tie"
        )
        assert_oracle_invariants(self, halted)
        self.assertTrue(halted["event_requested"])
        self.assertFalse(halted["event_observed"])
        self.assertFalse(halted["cancellation_observed"])
        self.assertFalse(halted["timeout_observed"])
        self.assertFalse(halted["tie_resolved_to_cancellation"])
        self.assertEqual(halted["observed_interruption_name"], "none")
        self.assertEqual(halted["preempted_transition_input"], "none")
        self.assertFalse(halted["rollback_performed"])
        self.assertEqual(halted["terminal"], "rejected-transition")

        baseline = reference_state_machine()
        self.assertFalse(baseline["event_requested"])
        self.assertFalse(baseline["event_observed"])
        self.assertEqual(baseline["observed_interruption_name"], "none")
        self.assertEqual(baseline["preempted_transition_input"], "none")
        self.assertFalse(any(baseline["rollback_executed"]))
        self.assertTrue(
            all(math.isnan(value) for value in baseline["rollback_source_ids"])
        )
        self.assertTrue(
            all(
                math.isnan(value)
                for row in baseline["rollback_state_trace"]
                for value in row
            )
        )

    def test_broken_last_request_wins_exposes_false_approval(self):
        strict = reference_state_machine(scenario_mode="fault-reset-conflict")
        broken = reference_state_machine(
            scenario_mode="fault-reset-conflict",
            arbitration_mode="last-request-wins",
        )
        strict_without_safe_off = reference_state_machine(
            p09_safe_off_proof=False,
            scenario_mode="fault-reset-conflict",
        )
        broken_without_safe_off = reference_state_machine(
            p09_safe_off_proof=False,
            scenario_mode="fault-reset-conflict",
            arbitration_mode="last-request-wins",
        )
        for result in (strict, broken):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["sequence_completed"])
            self.assertEqual(result["sequence_final_state_id"], OFF)
        for result in (strict_without_safe_off, broken_without_safe_off):
            assert_oracle_invariants(self, result)
        self.assertTrue(strict["strict_accepted"])
        self.assertTrue(strict["reported_accepted"])
        self.assertFalse(strict["false_approval"])
        self.assertEqual(strict["recovery_count"], 2)
        self.assertEqual(strict["recovery_qualified_step"], 9)

        conflict_index = 6
        self.assertEqual(broken["source_state_ids"][conflict_index], ACTIVE)
        self.assertEqual(broken["strict_requested_state_ids"][conflict_index], FAULT)
        self.assertEqual(broken["reported_requested_state_ids"][conflict_index], READY)
        self.assertEqual(broken["observed_state_ids"][conflict_index], READY)
        self.assertEqual(
            strict["transition_input_matrix"], broken["transition_input_matrix"]
        )
        self.assertEqual(
            strict["strict_selected_inputs"][conflict_index], "feedback-loss"
        )
        self.assertEqual(
            strict["reported_selected_inputs"][conflict_index], "feedback-loss"
        )
        self.assertEqual(
            broken["strict_selected_inputs"][conflict_index], "feedback-loss"
        )
        self.assertEqual(
            broken["reported_selected_inputs"][conflict_index], "reset-request"
        )
        self.assertTrue(broken["transition_table_allowed"][conflict_index])
        self.assertFalse(broken["reported_transition_table_allowed"][conflict_index])
        self.assertTrue(broken["strict_guard_pass"][conflict_index])
        self.assertFalse(broken["reported_guard_pass"][conflict_index])
        self.assertFalse(broken["strict_postcondition_pass"][conflict_index])
        self.assertTrue(broken["reported_postcondition_pass"][conflict_index])
        self.assertFalse(broken["strict_transition_pass"][conflict_index])
        self.assertFalse(broken["reported_transition_pass"][conflict_index])
        self.assertTrue(broken["policy_step_accepted"][conflict_index])
        self.assertTrue(broken["priority_violation"][conflict_index])
        self.assertTrue(broken["guard_bypassed"][conflict_index])
        self.assertEqual(broken["recovery_count"], 0)
        self.assertTrue(math.isnan(broken["recovery_qualified_step"]))
        self.assertFalse(broken["strict_accepted"])
        self.assertTrue(broken["reported_accepted"])
        self.assertTrue(broken["false_approval"])
        self.assertFalse(broken["decision_correct"])
        self.assertEqual(broken["transition_violation_count"], 1)
        self.assertEqual(broken["reported_violation_count"], 1)
        self.assertEqual(broken["policy_violation_count"], 0)
        self.assertEqual(broken["priority_violation_count"], 1)
        self.assertEqual(broken["terminal"], "completed-false-approval")
        self.assertEqual(broken["failure"], "fault-priority-bypassed")
        self.assertEqual(
            broken["reporting_failure"], "last-request-wins-false-approval"
        )
        self.assertEqual(
            broken["state_id_trace"],
            [
                STANDBY,
                STANDBY,
                READY,
                READY,
                READY,
                ACTIVE,
                READY,
                READY,
                READY,
                READY,
                READY,
                SAFE_HOLD,
                OFF,
            ],
        )
        self.assertEqual(strict_without_safe_off["first_violation_step"], 13)
        self.assertEqual(strict_without_safe_off["priority_violation_count"], 0)
        self.assertEqual(
            strict_without_safe_off["failure"], "p09-safe-off-proof-unavailable"
        )
        self.assertEqual(broken_without_safe_off["first_violation_step"], 7)
        self.assertEqual(broken_without_safe_off["priority_violation_count"], 1)
        self.assertEqual(broken_without_safe_off["transition_violation_count"], 2)
        self.assertFalse(broken_without_safe_off["false_approval"])
        self.assertEqual(broken_without_safe_off["terminal"], "rejected-transition")
        self.assertEqual(
            broken_without_safe_off["failure"], "fault-priority-bypassed"
        )
        self.assertEqual(broken_without_safe_off["reporting_failure"], "none")

    def test_recovery_and_call_isolation_have_no_hidden_state(self):
        expected = reference_state_machine()
        normalized = reference_state_machine(
            2.0,
            2.0,
            1,
            1,
            " NOMINAL ",
            " NONE ",
            " GUARDED-PRIORITY ",
        )
        self.assertEqual(normalized, expected)
        broken = reference_state_machine(
            scenario_mode="fault-reset-conflict",
            arbitration_mode="last-request-wins",
        )
        broken["state_id_trace"][0] = 999
        broken["state_occupancy_trace"][0][0] = 999
        cancelled = reference_state_machine(event_mode="cancellation")
        cancelled["rollback_observed_ids"][0] = 999
        for kwargs in (
            {"readiness_confirmations": 0},
            {"recovery_confirmations": 5},
            {"p09_startup_proof": "true"},
            {"p09_safe_off_proof": None},
            {"scenario_mode": "unsupported"},
            {"event_mode": "late"},
            {"arbitration_mode": "first-request-wins"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                reference_state_machine(**kwargs)
        for input_name in ("p09_startup_proof", "p09_safe_off_proof"):
            for invalid in (
                2,
                -1,
                0.5,
                math.nan,
                math.inf,
                1 + 1j,
                [True],
                "true",
                None,
            ):
                with self.subTest(input_name=input_name, invalid=invalid):
                    with self.assertRaises(ValueError):
                        reference_state_machine(**{input_name: invalid})
        recovered = reference_state_machine()
        self.assertEqual(recovered, expected)
        self.assertNotEqual(recovered["state_id_trace"][0], 999)
        self.assertNotEqual(recovered["state_occupancy_trace"][0][0], 999)
        self.assertTrue(math.isnan(recovered["rollback_observed_ids"][0]))

    def test_every_supported_terminal_is_behaviorally_reachable(self):
        scenarios = [
            reference_state_machine(),
            reference_state_machine(scenario_mode="premature-activation"),
            reference_state_machine(
                scenario_mode="fault-reset-conflict",
                arbitration_mode="last-request-wins",
            ),
            reference_state_machine(event_mode="cancellation"),
            reference_state_machine(event_mode="timeout"),
            reference_state_machine(
                p09_safe_off_proof=False, event_mode="cancellation"
            ),
            reference_state_machine(p09_safe_off_proof=False, event_mode="timeout"),
        ]
        self.assertEqual(
            {scenario["terminal"] for scenario in scenarios},
            {
                "completed-off",
                "rejected-transition",
                "completed-false-approval",
                "cancelled-rollback-complete",
                "timed-out-rollback-complete",
                "cancelled-rollback-incomplete",
                "timed-out-rollback-incomplete",
            },
        )

    def test_transition_input_inventory_is_bounded_and_conflict_is_explicit(self):
        nominal = reference_state_machine()
        recoverable = reference_state_machine(
            scenario_mode="recoverable-feedback-loss"
        )
        strict_conflict = reference_state_machine(
            scenario_mode="fault-reset-conflict"
        )
        broken_conflict = reference_state_machine(
            scenario_mode="fault-reset-conflict",
            arbitration_mode="last-request-wins",
        )
        for result in (nominal, recoverable, strict_conflict, broken_conflict):
            assert_oracle_invariants(self, result)
            self.assertEqual(len(result["transition_input_names"]), 9)
            self.assertEqual(len(result["transition_input_matrix"]), 13)
            self.assertLessEqual(max(result["transition_input_count"]), 2)
        self.assertEqual(nominal["transition_input_count"], [1] * 13)
        self.assertFalse(any(nominal["transition_input_conflict"]))
        self.assertEqual(recoverable["transition_input_count"], [1] * 13)
        self.assertFalse(any(recoverable["transition_input_conflict"]))
        expected_counts = [1] * 13
        expected_counts[6] = 2
        expected_conflicts = [False] * 13
        expected_conflicts[6] = True
        for result in (strict_conflict, broken_conflict):
            self.assertEqual(result["transition_input_count"], expected_counts)
            self.assertEqual(result["transition_input_conflict"], expected_conflicts)
            self.assertEqual(
                [
                    name
                    for name, asserted in zip(
                        result["transition_input_names"],
                        result["transition_input_matrix"][6],
                    )
                    if asserted
                ],
                ["feedback-loss", "reset-request"],
            )

    def test_experiment_has_ordered_baseline_two_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sweep_sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sweep_sections), 2)
        for marker in (
            "baseline = model(2,2,true,true",
            "trial = model(readinessSweep(k),2,true,true",
            "trial = model(2,recoverySweep(k),true,true",
            "[2 2 3 3 3 4 4 4 4 4 4 6 1]",
            "readinessSweep = 1:4",
            "readyStepByConfirmation",
            "[2 3 4 5]",
            "standbyObservationsByConfirmation",
            "[1 2 3 4]",
            "recoverySweep = 1:4",
            "recoveryStepByConfirmation",
            "[8 9 10 11]",
            "faultObservationsByConfirmation",
            "startupProofMissing",
            "safeOffProofMissing",
            "prematureActivation",
            "stuckState",
            "strictGuardPass(7)",
            "strictPostconditionPass(7)",
            "cancelled",
            "timedOut",
            "cancellation-timeout-tie",
            "expectedEvaluatedBeforeEvent",
            "expectedRollbackTrace",
            "rollbackComplete",
            "cancelled-rollback-incomplete",
            "isequaln(recovered,baseline)",
            "strictConflict",
            "last-request-wins",
            "strictRequestedStateId(7) == 5",
            "reportedRequestedStateId(7) == 3",
            "transitionInputMatrix",
            "transitionInputCount(7) == 2",
            "transitionInputConflict(7)",
            "guardBypassed(7)",
            "policyStepAccepted(7)",
            "broken.falseApproval",
        ):
            self.assertIn(marker, experiment)
        self.assertLess(experiment.index("%% Baseline"), experiment.index("%% Sweep 1"))
        self.assertLess(
            experiment.index("Mechanism after lever 1"),
            experiment.index("%% Sweep 2"),
        )
        self.assertLess(
            experiment.index("Mechanism after lever 2"),
            experiment.index("%% Negative cases"),
        )
        self.assertLess(
            experiment.index("%% Negative cases"),
            experiment.index("%% Broken case"),
        )
        self.assertGreaterEqual(experiment.count("figure("), 5)
        self.assertIn("stairs(", experiment)
        self.assertIn("bar(", experiment)
        for unit in (
            "Observation/event step (-)",
            "confirmations (count)",
            "observations %d count",
            "Transition evidence (Boolean -)",
            "State ID (-)",
        ):
            self.assertIn(unit, experiment)
        self.assertIn("dimensionless", experiment)
        self.assertIn("not recovery duration", experiment)

    def test_launch_path_retains_read_context_and_asks_one_prediction(self):
        lesson = self.read("lesson.m")
        experiment = self.read("experiment.m")
        prediction_pattern = r"disp\(\s*'Prediction:"

        self.assertEqual(lesson.count("experiment;"), 1)
        self.assertEqual(
            len(re.findall(prediction_pattern, lesson + "\n" + experiment)),
            1,
        )
        self.assertFalse(re.search(r"(?m)^\s*clc\b", experiment))
        self.assertLess(lesson.index("%% Read"), lesson.index("experiment;"))
        self.assertLess(
            re.search(prediction_pattern, experiment).start(),
            experiment.index("%% Baseline"),
        )

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertEqual(interactive.count("uispinner"), 2)
        self.assertEqual(interactive.count("uicheckbox"), 2)
        self.assertEqual(interactive.count("uidropdown"), 3)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 7)
        self.assertEqual(interactive.count("'Limits',[1 4]"), 2)
        for marker in (
            "scenarioControl.ItemsData",
            "eventControl.ItemsData",
            "arbitrationControl.ItemsData",
            "recoverable-feedback-loss",
            "fault-reset-conflict",
            "state-stuck-active",
            "premature-activation",
            "cancellation-timeout-tie",
            "last-request-wins",
            "resetBaseline",
            "readinessControl.Value = 2",
            "recoveryControl.Value = 2",
            "p09StartupControl.Value = true",
            "p09SafeOffControl.Value = true",
            "scenarioControl.Value = 'nominal'",
            "eventControl.Value = 'none'",
            "arbitrationControl.Value = 'guarded-priority'",
            "transitionTableAllowed",
            "strictGuardPass",
            "strictPostconditionPass",
            "false approval",
            "priority violations",
            "rollback complete",
            "rollback failure",
        ):
            self.assertIn(marker, interactive)
        self.assertIn("Observation/event step is dimensionless", interactive)
        self.assertIn("asserted facts", interactive)
        self.assertIn("Transition evidence (Boolean -)", interactive)

    def test_checks_cover_exact_oracles_malformed_inputs_and_isolation(self):
        checks = self.read("run_checks.m")
        for marker in (
            "expectedStateNames",
            "expectedEventNames",
            "expectedRollbackEventNames",
            "expectedTransitionInputNames",
            "expectedTransitionTable",
            "expectedBaselineTrace",
            "[2 2 3 3 3 4 4 4 4 4 4 6 1]",
            "expectedRecoverableTrace",
            "[2 2 3 3 3 4 5 5 3 3 3 6 1]",
            "readinessMinimum",
            "readinessMaximum",
            "recoveryMinimum",
            "recoveryMaximum",
            "[2 3 4 5]",
            "[8 9 10 11]",
            "startupProofMissing",
            "safeOffProofMissing",
            "prematureActivation",
            "stuckState",
            "cancelled",
            "timedOut",
            "tied",
            "cancelledIncomplete",
            "timedOutIncomplete",
            "tiedIncomplete",
            "expectedEvaluatedBeforeEvent",
            "expectedRollbackTrace",
            "strictConflict",
            "broken",
            "strictConflictWithoutSafeOff",
            "brokenWithoutSafeOff",
            "strictRequestedStateId(7)",
            "reportedRequestedStateId(7)",
            "reportedTransitionTableAllowed(7)",
            "reportedGuardPass(7)",
            "guardBypassed(7)",
            "policyStepAccepted(7)",
            "transitionInputCount(7)",
            "maximumSimultaneousTransitionInputs",
            "string(' NOMINAL ')",
            "P10:InvalidReadinessConfirmations",
            "P10:InvalidRecoveryConfirmations",
            "P10:InvalidP09StartupProof",
            "P10:InvalidP09SafeOffProof",
            "P10:InvalidScenarioMode",
            "P10:InvalidEventMode",
            "P10:InvalidArbitrationMode",
            "afterMalformed",
            "afterCancellation",
            "afterTimeout",
            "afterIncompleteRollback",
            "afterBroken",
            "assertStateMachineInvariant",
            "P10 checks passed",
        ):
            self.assertIn(marker, checks)
        self.assertIn("transitionCount == 13", checks)
        self.assertIn("stateCount == 6", checks)
        self.assertIn("rollbackTransitionCount == 3", checks)
        self.assertIn("size(out.transitionInputMatrix)", checks)
        self.assertIn("size(out.stateOccupancyTrace)", checks)

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
        self.assertGreaterEqual(
            len(re.findall(r"^%% ", self.read("lesson.m"), flags=re.MULTILINE)),
            4,
        )
        for marker in (
            "P09",
            "P11",
            "P12",
            "P13",
            "P18",
            "input",
            "observable",
            "failure",
            "OFF",
            "STANDBY",
            "READY",
            "ACTIVE",
            "FAULT",
            "SAFE-HOLD",
            "transition table",
            "guard",
            "postcondition",
            "priority",
            "confirmation",
            "premature",
            "cancellation",
            "timeout",
            "rollback",
            "recovery",
            "interpretation",
            "teach-back",
        ):
            self.assertIn(marker.lower(), combined.lower())
        flattened = re.sub(r"\s+", " ", combined)
        self.assertIn(
            "p09StartupProof = startupOrderValid AND startupFinalRunning",
            flattened,
        )
        self.assertIn(
            "p09SafeOffProof = shutdownOrderValid AND shutdownFinalSafeOff",
            flattened,
        )
        self.assertIn("does not consume P09's `rollbackPerformed`", flattened)
        self.assertIn("`rollbackSafeHold`", flattened)
        self.assertIn("do not command electrical power", flattened)
        self.assertIn("Observation/event step is dimensionless", flattened)
        self.assertIn("no sample period", flattened)
        self.assertIn("not physical equipment or personnel-safety evidence", flattened)
        launch_sources = self.read("lesson.m") + "\n" + self.read("experiment.m")
        self.assertEqual(launch_sources.lower().count("prediction:"), 1)

    def test_p09_compatibility_is_composite_consumed_and_not_reimplemented(self):
        p09_model = (
            ROOT / "modules/09-design-startup-and-shutdown-sequences/model.m"
        ).read_text(encoding="utf-8")
        for prerequisite_fact in (
            "startupOrderValid",
            "startupFinalRunning",
            "shutdownOrderValid",
            "shutdownFinalSafeOff",
            "rollbackSafeHold",
        ):
            self.assertIn(prerequisite_fact, p09_model)

        model = self.read("model.m")
        self.assertIn(
            "p09StartupProof = startupOrderValid && startupFinalRunning",
            model,
        )
        self.assertIn(
            "p09SafeOffProof = shutdownOrderValid && shutdownFinalSafeOff",
            model,
        )
        self.assertNotIn("rollbackSafeHold", model)
        self.assertNotIn("p09RollbackPerformed", model)
        self.assertNotIn("run_module_checks", model)
        self.assertNotIn("power-request", model)
        self.assertNotIn("power-off-request", model)
        self.assertIn("enter-standby-request", model)
        self.assertIn("off-request", model)
        self.assertIn("return-off-after-p09-proof", model)

    def test_cli_lifecycle_resolves_p10_identity_without_frontier_assumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            shutil.copytree(P10, fixture / self.module["folder"])
            (fixture / "curriculum").mkdir(parents=True)
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"

            started = subprocess.run(
                [str(fixture / "bin/learn"), "start", "P10"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            checked = subprocess.run(
                [str(fixture / "bin/learn"), "check", "P10"],
                cwd=fixture,
                text=True,
                capture_output=True,
                env=environment,
                timeout=10,
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn("P10 — Model System States and Transitions", started.stdout)
            self.assertIn(f"Guiding question: {QUESTION}", started.stdout)
            self.assertIn("launch_lesson('P10')", started.stdout)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("run_module_checks('P10')", checked.stdout)
            state = json.loads(
                (fixture / ".learning/progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P10")
            self.assertEqual(state["completed"], {})
            self.assertEqual(state["notes"], {})

    def test_rollback_fixture_recovers_persisted_p10_to_p09_without_erasure(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 10:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            retained_note = "P10 state/transition teach-back retained"
            (state_dir / "progress.json").write_text(
                json.dumps(
                    {
                        "current": "P10",
                        "completed": {"P10": True},
                        "notes": {"P10": retained_note},
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
            self.assertIn("P09 — Design Startup and Shutdown Sequences", recovered.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn(
                f"{manifest['module_count']} total, {implemented_count} implemented, 0 completed",
                status.stdout,
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            p10_line = next(line for line in listing.stdout.splitlines() if " P10 " in line)
            self.assertTrue(p10_line.startswith("○ P10"), p10_line)
            self.assertNotIn("✓ P10", listing.stdout)
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P09")
            self.assertTrue(state["completed"]["P10"])
            self.assertEqual(state["notes"]["P10"], retained_note)

    def test_retained_evidence_has_required_sections_and_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P10-*.md"))
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
            "deployment",
            "production",
        ):
            self.assertIn(marker, evidence)


if __name__ == "__main__":
    unittest.main()
