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
P05 = ROOT / "modules/05-allocate-functions-across-hardware-and-software"
P04_MODEL = ROOT / "modules/04-decompose-a-system-into-functions/model.m"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you allocate "
    "Functions Across Hardware and Software?"
)
FUNCTION_NAMES = [
    "Capture intent",
    "Validate authority",
    "Observe position",
    "Compute error",
    "Generate correction",
    "Update physical state",
    "Confirm requested behavior",
    "Handle cancellation",
    "Enforce deadline",
    "Report outcome",
]
SOFTWARE_COSTS = [2.0, 2.0, 0.0, 6.0, 8.0, 0.0, 4.0, 2.0, 2.0, 2.0]
HARDWARE_COSTS = [0.0, 3.0, 5.0, 7.0, 9.0, 8.0, 0.0, 3.0, 3.0, 0.0]
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


def matlab_cell_array_contract(source: str, variable: str) -> tuple[tuple[str, ...], str]:
    """Return exact values plus whitespace-insensitive MATLAB cell-array structure."""
    match = re.search(
        rf"\b{re.escape(variable)}\s*=\s*\{{(.*?)\}}\s*;",
        source,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"MATLAB cell array {variable} was not found")
    body = match.group(1)
    values = tuple(re.findall(r"'([^']*)'", body))
    structure = re.sub(r"\s+", "", re.sub(r"'[^']*'", "''", body))
    return values, structure


def reference_allocation(
    control_owner: str = "software",
    supervision_owner: str = "hardware",
    software_capacity: float = 30.0,
    hardware_capacity: float = 40.0,
    software_state: str = "available",
    event_mode: str = "none",
    assessment_mode: str = "complete",
) -> dict[str, object]:
    """Independent Python oracle for the documented P05 allocation contract."""
    owners = ["unassigned"] * len(FUNCTION_NAMES)
    for index in (0, 6, 9):
        owners[index] = "software"
    for index in (2, 5):
        owners[index] = "hardware"
    for index in (3, 4):
        owners[index] = control_owner
    for index in (1, 7, 8):
        owners[index] = supervision_owner

    software_owned = [owner == "software" for owner in owners]
    hardware_owned = [owner == "hardware" for owner in owners]
    software_contributions = [
        cost if selected else 0.0
        for cost, selected in zip(SOFTWARE_COSTS, software_owned)
    ]
    hardware_contributions = [
        cost if selected else 0.0
        for cost, selected in zip(HARDWARE_COSTS, hardware_owned)
    ]
    software_demand = sum(software_contributions)
    hardware_demand = sum(hardware_contributions)
    software_fit = software_demand <= software_capacity
    hardware_fit = hardware_demand <= hardware_capacity
    resource_fit = software_fit and hardware_fit
    binding_valid = all(software_owned[index] for index in (0, 6, 9)) and all(
        hardware_owned[index] for index in (2, 5)
    )

    software_available = software_state == "available"
    software_execution_available = software_available and software_fit
    hardware_execution_available = hardware_fit
    function_available = [
        (software and software_execution_available)
        or (hardware and hardware_execution_available)
        for software, hardware in zip(software_owned, hardware_owned)
    ]
    all_functions_available = all(function_available)
    independent_supervision = all(hardware_owned[index] for index in (1, 7, 8))
    event_index = {"none": None, "cancellation": 7, "deadline": 8}[event_mode]
    if event_index is None:
        event_handled = True
        safe_hold_request_available = False
        scenario_requirement_met = all_functions_available
    else:
        event_handled = function_available[event_index]
        safe_hold_request_available = event_handled
        scenario_requirement_met = event_handled

    allocation_contract_met = (
        resource_fit
        and binding_valid
        and independent_supervision
        and scenario_requirement_met
    )
    resource_only = resource_fit and binding_valid
    reported_feasible = (
        allocation_contract_met
        if assessment_mode == "complete"
        else resource_only
    )
    false_feasible = reported_feasible and not allocation_contract_met

    if not resource_fit:
        scenario_status = "resource-overload"
    elif event_mode == "none":
        scenario_status = (
            "nominal-ready"
            if all_functions_available
            else "software-common-mode-loss"
        )
    elif event_handled:
        scenario_status = f"{event_mode}-contained"
    else:
        scenario_status = f"{event_mode}-unhandled"

    if not software_fit and not hardware_fit:
        failure_mode = "dual-capacity-exceeded"
    elif not software_fit:
        failure_mode = "software-capacity-exceeded"
    elif not hardware_fit:
        failure_mode = "hardware-capacity-exceeded"
    elif not binding_valid:
        failure_mode = "fixed-binding-violated"
    elif event_mode != "none" and not event_handled:
        failure_mode = f"{event_mode}-unhandled"
    elif event_mode == "none" and not all_functions_available:
        failure_mode = "required-functions-unavailable"
    elif not independent_supervision:
        failure_mode = "common-mode-supervision"
    else:
        failure_mode = "none"

    def utilization(demand: float, capacity: float) -> float:
        if capacity == 0:
            return 0.0 if demand == 0 else math.inf
        return 100.0 * demand / capacity

    return {
        "owners": owners,
        "software_owned": software_owned,
        "hardware_owned": hardware_owned,
        "software_contributions": software_contributions,
        "hardware_contributions": hardware_contributions,
        "software_demand": software_demand,
        "hardware_demand": hardware_demand,
        "software_margin": software_capacity - software_demand,
        "hardware_margin": hardware_capacity - hardware_demand,
        "software_utilization": utilization(software_demand, software_capacity),
        "hardware_utilization": utilization(hardware_demand, hardware_capacity),
        "software_fit": software_fit,
        "hardware_fit": hardware_fit,
        "resource_fit": resource_fit,
        "binding_valid": binding_valid,
        "software_execution_available": software_execution_available,
        "hardware_execution_available": hardware_execution_available,
        "function_available": function_available,
        "lost_functions": [
            name
            for name, available in zip(FUNCTION_NAMES, function_available)
            if not available
        ],
        "all_functions_available": all_functions_available,
        "independent_supervision": independent_supervision,
        "event_index": event_index,
        "event_handled": event_handled,
        "safe_hold_request_available": safe_hold_request_available,
        "scenario_requirement_met": scenario_requirement_met,
        "allocation_contract_met": allocation_contract_met,
        "resource_only": resource_only,
        "reported_feasible": reported_feasible,
        "false_feasible": false_feasible,
        "scenario_status": scenario_status,
        "failure_mode": failure_mode,
    }


class P05ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P05")

    def read(self, name: str) -> str:
        return (P05 / name).read_text(encoding="utf-8")

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
                "number": 5,
                "id": "P05",
                "title": "Allocate Functions Across Hardware and Software",
                "guiding_question": QUESTION,
                "phase": 2,
                "phase_title": "Allocation and interfaces",
                "slug": "allocate-functions-across-hardware-and-software",
                "folder": "modules/05-allocate-functions-across-hardware-and-software",
                "implementation_batch": "P05",
                "prerequisites": ["P04"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P04"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P05.iterdir() if path.is_file()}
        )

    def test_owned_artifacts_have_no_residue_and_exactly_one_terminal_newline(self):
        for name in sorted(REQUIRED_ARTIFACTS):
            path = P05 / name
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
        matlab_code = re.sub(r"\s+|\.\.\.", "", model)
        self.assertIn("function out = model(", model)
        self.assertIn("maxCapacityUnits = 1000", model)
        self.assertIn(
            "softwareCostUnitsPerUpdate = [2; 2; 0; 6; 8; 0; 4; 2; 2; 2]",
            compact,
        )
        self.assertIn(
            "hardwareCostAllocationUnits = [0; 3; 5; 7; 9; 8; 0; 3; 3; 0]",
            compact,
        )
        self.assertIn("fixedSoftwareIndices = [1 7 10]", compact)
        self.assertIn("fixedHardwareIndices = [3 6]", compact)
        self.assertIn("controlFunctionIndices = [4 5]", compact)
        self.assertIn("supervisionFunctionIndices = [2 8 9]", compact)
        self.assertIn("sum(softwareContributionUnits)", model)
        self.assertIn("sum(hardwareContributionUnits)", model)
        self.assertIn("softwareCapacity - softwareDemandUnitsPerUpdate", model)
        self.assertIn("hardwareCapacity - hardwareDemandAllocationUnits", model)
        self.assertIn("softwareFaultIndependentSupervision", model)
        self.assertIn("safeHoldRequestAvailable", model)
        self.assertIn("falseFeasible", model)
        self.assertIn("P05:InvalidCapacity", model)
        self.assertIn("P05:ResourceBound", model)
        for critical_fragment in (
            "functionOwner(fixedSoftwareIndices)=repmat({'software'},numel(fixedSoftwareIndices),1);",
            "functionOwner(fixedHardwareIndices)=repmat({'hardware'},numel(fixedHardwareIndices),1);",
            "functionOwner(controlFunctionIndices)=repmat({controlOwner},numel(controlFunctionIndices),1);",
            "functionOwner(supervisionFunctionIndices)=repmat({supervisionOwner},numel(supervisionFunctionIndices),1);",
            "softwareExecutionAvailable=softwareAvailable&&softwareResourceFit;",
            "hardwareExecutionAvailable=hardwareResourceFit;",
            "softwareResourceFit=softwareDemandUnitsPerUpdate<=softwareCapacity;",
            "hardwareResourceFit=hardwareDemandAllocationUnits<=hardwareCapacity;",
            "functionAvailable=(softwareOwned&softwareExecutionAvailable)|(hardwareOwned&hardwareExecutionAvailable);",
            "ifstrcmp(eventMode,'cancellation')eventFunctionIndex=8;",
            "elseifstrcmp(eventMode,'deadline')eventFunctionIndex=9;",
            "ifeventFunctionIndex==0eventGuardAvailable=true;eventHandled=true;safeHoldRequestAvailable=false;scenarioRequirementMet=allRequiredFunctionsAvailable;else",
            "eventGuardAvailable=functionAvailable(eventFunctionIndex);",
            "safeHoldRequestAvailable=eventGuardAvailable;",
            "allocationContractMet=nominalResourceFit&&bindingValid&&softwareFaultIndependentSupervision&&scenarioRequirementMet;",
            "resourceOnlyDecision=nominalResourceFit&&bindingValid;",
            "ifstrcmp(assessmentMode,'complete')reportedFeasible=allocationContractMet;elsereportedFeasible=resourceOnlyDecision;end",
            "falseFeasible=reportedFeasible&&~allocationContractMet;",
            "elseifstrcmp(eventMode,'none')ifallRequiredFunctionsAvailablescenarioStatus='nominal-ready';elsescenarioStatus='software-common-mode-loss';end",
            "elseifstrcmp(eventMode,'none')&&~allRequiredFunctionsAvailablefailureMode='required-functions-unavailable';",
            "out.eventFunctionIndex=eventFunctionIndex;",
            "out.allocationContractMet=allocationContractMet;",
            "out.resourceOnlyDecision=resourceOnlyDecision;",
            "out.reportedFeasible=reportedFeasible;",
        ):
            self.assertIn(critical_fragment, matlab_code)
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
            "intlinprog(",
            "optimproblem(",
            "fmincon(",
            "ga(",
            "lsim(",
            "tf(",
            "sim(",
        ):
            self.assertNotIn(forbidden, model.lower())

    def test_p04_function_contracts_are_preserved_exactly(self):
        p04 = P04_MODEL.read_text(encoding="utf-8")
        p05 = self.read("model.m")
        for variable in (
            "functionNames",
            "functionInputs",
            "functionOutputs",
            "functionFailureModes",
        ):
            with self.subTest(variable=variable):
                self.assertEqual(
                    matlab_cell_array_contract(p05, variable),
                    matlab_cell_array_contract(p04, variable),
                )

    def test_independent_oracle_covers_baseline_and_all_owner_combinations(self):
        baseline = reference_allocation()
        self.assertEqual(baseline["software_demand"], 22.0)
        self.assertEqual(baseline["hardware_demand"], 22.0)
        self.assertEqual(baseline["software_margin"], 8.0)
        self.assertEqual(baseline["hardware_margin"], 18.0)
        self.assertAlmostEqual(baseline["software_utilization"], 100 * 22 / 30)
        self.assertEqual(baseline["hardware_utilization"], 55.0)
        self.assertTrue(baseline["allocation_contract_met"])
        self.assertEqual(baseline["failure_mode"], "none")
        self.assertEqual(
            baseline["owners"],
            [
                "software",
                "hardware",
                "hardware",
                "software",
                "software",
                "hardware",
                "software",
                "hardware",
                "hardware",
                "software",
            ],
        )

        hardware_control = reference_allocation(control_owner="hardware")
        software_supervision = reference_allocation(supervision_owner="software")
        both_moved = reference_allocation(
            control_owner="hardware", supervision_owner="software"
        )
        self.assertEqual(
            (hardware_control["software_demand"], hardware_control["hardware_demand"]),
            (8.0, 38.0),
        )
        self.assertEqual(
            (
                software_supervision["software_demand"],
                software_supervision["hardware_demand"],
            ),
            (28.0, 13.0),
        )
        self.assertEqual(
            (both_moved["software_demand"], both_moved["hardware_demand"]),
            (14.0, 29.0),
        )
        self.assertFalse(software_supervision["independent_supervision"])
        self.assertFalse(software_supervision["allocation_contract_met"])
        self.assertEqual(software_supervision["failure_mode"], "common-mode-supervision")

        for result in (baseline, hardware_control, software_supervision, both_moved):
            self.assertTrue(
                all(
                    software != hardware
                    for software, hardware in zip(
                        result["software_owned"], result["hardware_owned"]
                    )
                )
            )
            self.assertTrue(result["binding_valid"])

    def test_independent_oracle_covers_capacity_limits_and_overload(self):
        exact = reference_allocation(software_capacity=22, hardware_capacity=22)
        self.assertTrue(exact["resource_fit"])
        self.assertTrue(exact["allocation_contract_met"])
        self.assertEqual(exact["software_margin"], 0.0)
        self.assertEqual(exact["hardware_margin"], 0.0)
        self.assertEqual(exact["software_utilization"], 100.0)
        self.assertEqual(exact["hardware_utilization"], 100.0)

        software_below = reference_allocation(
            software_capacity=21.999, hardware_capacity=22
        )
        hardware_below = reference_allocation(
            software_capacity=22, hardware_capacity=21.999
        )
        dual_below = reference_allocation(
            software_capacity=21.999, hardware_capacity=21.999
        )
        self.assertEqual(software_below["failure_mode"], "software-capacity-exceeded")
        self.assertEqual(hardware_below["failure_mode"], "hardware-capacity-exceeded")
        self.assertEqual(dual_below["failure_mode"], "dual-capacity-exceeded")
        zero = reference_allocation(software_capacity=0, hardware_capacity=0)
        self.assertFalse(zero["resource_fit"])
        self.assertFalse(zero["software_execution_available"])
        self.assertFalse(zero["hardware_execution_available"])
        self.assertFalse(any(zero["function_available"]))
        self.assertTrue(math.isinf(zero["software_utilization"]))
        self.assertTrue(math.isinf(zero["hardware_utilization"]))

    def test_independent_oracle_covers_cancellation_timeout_and_false_approval(self):
        hardware_cancel = reference_allocation(
            software_state="stalled", event_mode="cancellation"
        )
        hardware_deadline = reference_allocation(
            software_state="stalled", event_mode="deadline"
        )
        self.assertFalse(hardware_cancel["all_functions_available"])
        self.assertTrue(hardware_cancel["event_handled"])
        self.assertTrue(hardware_cancel["safe_hold_request_available"])
        self.assertTrue(hardware_cancel["allocation_contract_met"])
        self.assertEqual(hardware_cancel["scenario_status"], "cancellation-contained")
        self.assertTrue(hardware_deadline["event_handled"])
        self.assertTrue(hardware_deadline["safe_hold_request_available"])
        self.assertEqual(hardware_deadline["scenario_status"], "deadline-contained")

        resource_starved_guard = reference_allocation(
            hardware_capacity=21.999,
            software_state="stalled",
            event_mode="cancellation",
        )
        self.assertFalse(resource_starved_guard["hardware_execution_available"])
        self.assertFalse(resource_starved_guard["event_handled"])
        self.assertFalse(resource_starved_guard["safe_hold_request_available"])
        self.assertFalse(resource_starved_guard["allocation_contract_met"])
        self.assertEqual(resource_starved_guard["scenario_status"], "resource-overload")
        self.assertEqual(
            resource_starved_guard["failure_mode"], "hardware-capacity-exceeded"
        )

        software_cancel = reference_allocation(
            supervision_owner="software",
            software_state="stalled",
            event_mode="cancellation",
        )
        software_deadline = reference_allocation(
            supervision_owner="software",
            software_state="stalled",
            event_mode="deadline",
        )
        self.assertTrue(software_cancel["resource_fit"])
        self.assertFalse(software_cancel["event_handled"])
        self.assertFalse(software_cancel["safe_hold_request_available"])
        self.assertEqual(software_cancel["failure_mode"], "cancellation-unhandled")
        self.assertFalse(software_deadline["event_handled"])
        self.assertEqual(software_deadline["failure_mode"], "deadline-unhandled")

        broken = reference_allocation(
            supervision_owner="software",
            software_state="stalled",
            event_mode="cancellation",
            assessment_mode="resource-only",
        )
        self.assertTrue(broken["resource_only"])
        self.assertTrue(broken["reported_feasible"])
        self.assertTrue(broken["false_feasible"])
        self.assertFalse(broken["allocation_contract_met"])
        self.assertEqual(broken["owners"], software_cancel["owners"])
        self.assertEqual(
            broken["software_contributions"], software_cancel["software_contributions"]
        )
        self.assertEqual(
            broken["hardware_contributions"], software_cancel["hardware_contributions"]
        )

    def test_no_event_software_stall_has_behavioral_coverage(self):
        stalled_without_event = reference_allocation(
            software_state="stalled", event_mode="none"
        )
        self.assertEqual(
            (
                stalled_without_event["resource_fit"],
                stalled_without_event["software_execution_available"],
                stalled_without_event["hardware_execution_available"],
                stalled_without_event["all_functions_available"],
                stalled_without_event["safe_hold_request_available"],
                stalled_without_event["scenario_requirement_met"],
                stalled_without_event["allocation_contract_met"],
                stalled_without_event["reported_feasible"],
                stalled_without_event["scenario_status"],
                stalled_without_event["failure_mode"],
            ),
            (
                True,
                False,
                True,
                False,
                False,
                False,
                False,
                False,
                "software-common-mode-loss",
                "required-functions-unavailable",
            ),
        )
        self.assertEqual(
            stalled_without_event["lost_functions"],
            [
                "Capture intent",
                "Compute error",
                "Generate correction",
                "Confirm requested behavior",
                "Report outcome",
            ],
        )

        checks = self.read("run_checks.m")
        self.assertIn(
            "stalledWithoutEvent = model('software','hardware',30,40,",
            checks,
        )
        self.assertIn(
            "A no-event stalled scenario must not be called transaction-ready.",
            checks,
        )

    def test_experiment_has_baselines_two_isolated_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sections), 2)
        self.assertIn("controlSweep = {'software','hardware'}", experiment)
        self.assertIn("supervisionSweep = {'hardware','software'}", experiment)
        self.assertIn("isequal(softwareDemandByControl,[22 8])", experiment)
        self.assertIn("isequal(hardwareDemandByControl,[22 38])", experiment)
        self.assertIn("isequal(guardAvailableBySupervision,[true false])", experiment)
        self.assertIn("'stalled','cancellation','resource-only'", experiment)
        self.assertIn("Broken assumption", experiment)
        self.assertIn("broken.falseFeasible", experiment)
        self.assertGreaterEqual(experiment.count("figure("), 5)
        self.assertGreaterEqual(experiment.count("xlabel("), 5)
        self.assertGreaterEqual(experiment.count("ylabel("), 5)
        for unit in (
            "work units/update",
            "allocation units",
            "(%)",
            "(-)",
            "Boolean -",
        ):
            self.assertIn(unit, experiment)
        self.assertIn("Mechanism after lever 1", experiment)
        self.assertLess(
            experiment.index("Mechanism after lever 1"), experiment.index("%% Sweep 2")
        )
        self.assertLess(
            experiment.index("Mechanism after lever 2"), experiment.index("%% Broken case")
        )
        self.assertIn("isequaln(recovered,baseline)", experiment)

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertGreaterEqual(interactive.count("uidropdown"), 5)
        self.assertGreaterEqual(interactive.count("uispinner"), 2)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 7)
        self.assertIn("'Limits',[0 60]", interactive)
        self.assertEqual(interactive.count("RoundFractionalValues = 'on'"), 2)
        self.assertIn("controlOwner.ItemsData = {'software','hardware'}", interactive)
        self.assertIn("supervisionOwner.ItemsData = {'hardware','software'}", interactive)
        self.assertIn("softwareState.ItemsData = {'available','stalled'}", interactive)
        self.assertIn("eventMode.ItemsData = {'none','cancellation','deadline'}", interactive)
        self.assertIn("assessmentMode.ItemsData = {'complete','resource-only'}", interactive)
        self.assertIn("resetBaseline", interactive)
        self.assertIn("Exactly one owner per function", interactive)
        self.assertIn(
            "displayUtilizationPercent(~isfinite(displayUtilizationPercent)) = 125",
            interactive,
        )
        self.assertIn("min(displayUtilizationPercent,125)", interactive)
        self.assertIn("safe-hold request available", interactive)
        self.assertIn("false feasible", interactive)

    def test_checks_cover_negative_recovery_isolation_compatibility_and_bounds(self):
        checks = self.read("run_checks.m")
        self.assertGreaterEqual(checks.count("assert("), 35)
        for marker in (
            "expectedFunctionNames",
            "expectedFunctionInputs",
            "expectedFunctionOutputs",
            "expectedFunctionFailureModes",
            "expectedSoftwareCosts",
            "expectedHardwareCosts",
            "hardwareControl",
            "softwareSupervision",
            "hardwareControlSoftwareSupervision",
            "exactCapacity",
            "softwareBelow",
            "hardwareBelow",
            "dualBelow",
            "zeroCapacities",
            "maxBounded",
            "hardwareCancel",
            "hardwareDeadline",
            "resourceStarvedGuard",
            "softwareCancel",
            "softwareDeadline",
            "stalledWithoutEvent",
            "brokenResourceOnly",
            "stateProbe",
            "uint8",
            "single",
            "string('software')",
            "P05:InvalidControlOwner",
            "P05:InvalidSupervisionOwner",
            "P05:InvalidSoftwareState",
            "P05:InvalidEventMode",
            "P05:InvalidAssessmentMode",
            "P05:InvalidCapacity",
            "P05:ResourceBound",
            "afterFailure",
            "afterIsolationProbe",
            "isequaln(baseline,repeat)",
            "functionCount == 10",
        ):
            self.assertIn(marker, checks)
        self.assertIn("P05 checks passed", checks)

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
            "P04",
            "P06",
            "P07",
            "P11",
            "D_sw",
            "margin",
            "work units",
            "allocation units",
            "input",
            "observable",
            "failure",
            "cancellation",
            "deadline",
            "timeout",
            "recovery",
            "teach-back",
            "interpretation",
        ):
            self.assertIn(marker.lower(), combined.lower())
        self.assertIn("not execution times", combined)
        self.assertIn("not evidence that physical safe hold", combined)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_rollback_fixture_recovers_persisted_p05_to_p04(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 5:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            (state_dir / "progress.json").write_text(
                json.dumps({"current": "P05", "completed": {}, "notes": {}}) + "\n",
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
            self.assertIn("P04 — Decompose a System into Functions", recovered.stdout)
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P04")

    def test_retained_evidence_exists_and_states_the_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P05-*.md"))
        self.assertTrue(evidence_files)
        evidence = "\n".join(
            path.read_text(encoding="utf-8") for path in evidence_files
        )
        for marker in (
            "Acceptance mapping",
            "Independent audit repairs",
            "Independent system-risk review repair",
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
        self.assertIn("Pass — completed lifecycle gate", evidence)
        self.assertIn("13 tests passed in 0.049 s", evidence)
        self.assertIn("58 tests passed in 1.008 s", evidence)
        self.assertIn("verify-20260823-084019.log", evidence)
        self.assertIn("14 tests passed in 0.059 s", evidence)
        self.assertIn("59 tests passed in 0.990 s", evidence)
        self.assertIn("59 tests passed in 0.904 s", evidence)
        self.assertIn("verify-20260823-085242.log", evidence)


if __name__ == "__main__":
    unittest.main()
