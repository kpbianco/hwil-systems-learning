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
P08 = ROOT / "modules/08-write-an-interface-control-contract"
QUESTION = (
    "What inputs, observable effects, and failure modes matter when you write an "
    "Interface Control Contract?"
)
CLAUSES = [
    "Interface identity",
    "Schema version",
    "Payload length",
    "Engineering unit",
    "Value range",
    "Sequence range",
    "Quality encoding",
    "Checksum integrity",
]
PAYLOAD_FIELDS = [
    "interface-id",
    "schema-version",
    "sequence",
    "angle",
    "quality",
    "checksum",
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


def matlab_round(value: float) -> int:
    """Match MATLAB's half-away-from-zero rule for checksum test values."""
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def reference_contract(
    source_angle: float = 30.021978021978,
    payload_words: int = 6,
    sender_version: int = 1,
    sequence: int = 42,
    source_quality: bool = True,
    fault_mode: str = "none",
    event_mode: str = "none",
    validation_mode: str = "complete",
) -> dict[str, object]:
    """Independent Python oracle for the documented P08 record contract."""
    interface_id = 801
    contract_version = 1
    required_words = 6
    maximum_sequence = 65535
    checksum_modulus = 65536

    cancellation = event_mode in {"cancellation", "cancellation-timeout-tie"}
    timeout = event_mode in {"timeout", "cancellation-timeout-tie"}
    event_observed = cancellation or timeout
    transfer_attempted = not event_observed

    transmitted_id = interface_id
    payload_value = source_angle
    payload_unit = "deg"
    transmitted_sequence = sequence
    quality_code = int(source_quality)
    if fault_mode == "identifier-mismatch":
        transmitted_id += 1
    elif fault_mode == "unit-mismatch":
        payload_value = source_angle * math.pi / 180
        payload_unit = "rad"
    elif fault_mode == "sequence-out-of-range":
        transmitted_sequence = maximum_sequence + 1
    elif fault_mode == "quality-code-invalid":
        quality_code = 2

    unit_code = 1 if payload_unit == "deg" else 2
    checksum_expected = (
        transmitted_id
        + sender_version
        + payload_words
        + transmitted_sequence
        + matlab_round(1000 * payload_value)
        + quality_code
        + unit_code
    ) % checksum_modulus
    transmitted_checksum = checksum_expected
    if fault_mode == "checksum-corruption":
        transmitted_checksum = (checksum_expected + 1) % checksum_modulus

    receiver_assumed_range_matches = -180 <= payload_value <= 180
    candidate_clauses = [
        transmitted_id == interface_id,
        sender_version == contract_version,
        payload_words == required_words,
        payload_unit == "deg",
        payload_unit == "deg" and receiver_assumed_range_matches,
        0 <= transmitted_sequence <= maximum_sequence
        and transmitted_sequence == round(transmitted_sequence),
        quality_code in {0, 1},
        transmitted_checksum == checksum_expected,
    ]
    clause_evaluated = [transfer_attempted] * len(CLAUSES)
    clause_pass = candidate_clauses if transfer_attempted else [False] * len(CLAUSES)
    visible_assumed_range_matches = (
        receiver_assumed_range_matches if transfer_attempted else False
    )
    conformant = transfer_attempted and all(clause_pass)
    value_plausible = (
        transfer_attempted
        and math.isfinite(payload_value)
        and visible_assumed_range_matches
    )

    if validation_mode == "complete":
        receiver_accepted = conformant
        receiver_released = receiver_accepted and quality_code == 1
    else:
        receiver_accepted = value_plausible
        receiver_released = receiver_accepted

    contract_eligible = conformant and quality_code == 1
    false_acceptance = receiver_accepted and not conformant
    false_release = receiver_released and not contract_eligible
    receiver_decision_correct = transfer_attempted and receiver_accepted == conformant
    p06_angle = payload_value if receiver_released else math.nan
    semantic_error = p06_angle - source_angle if receiver_released else math.nan
    semantic_preserved = receiver_released and abs(semantic_error) <= 1e-12
    p07_quality_preserved = (
        transfer_attempted
        and quality_code in {0, 1}
        and quality_code == int(source_quality)
    )
    p06_scalar_contract_met = (
        contract_eligible
        and math.isfinite(p06_angle)
        and semantic_preserved
    ) or (
        not contract_eligible and not receiver_released and math.isnan(p06_angle)
    )

    if cancellation:
        terminal = "cancelled"
    elif timeout:
        terminal = "timed-out"
    elif not receiver_accepted:
        terminal = "rejected"
    elif receiver_released:
        terminal = "accepted-and-released"
    else:
        terminal = "accepted-quality-withheld"

    if terminal == "cancelled":
        failure = "transfer-cancelled"
    elif terminal == "timed-out":
        failure = "transfer-timeout"
    elif not clause_pass[0]:
        failure = "identifier-mismatch"
    elif not clause_pass[1]:
        failure = "version-mismatch"
    elif not clause_pass[2]:
        failure = "payload-length-mismatch"
    elif not clause_pass[3]:
        failure = "unit-mismatch"
    elif not clause_pass[4]:
        failure = "angle-out-of-range"
    elif not clause_pass[5]:
        failure = "sequence-out-of-range"
    elif not clause_pass[6]:
        failure = "quality-code-invalid"
    elif not clause_pass[7]:
        failure = "checksum-mismatch"
    elif not source_quality:
        failure = "source-quality-invalid"
    else:
        failure = "none"

    if false_acceptance:
        reporting_failure = "value-only-false-acceptance"
    elif false_release:
        reporting_failure = "value-only-false-release"
    else:
        reporting_failure = "none"

    return {
        "source_angle": source_angle,
        "clause_evaluated": clause_evaluated,
        "clause_pass": clause_pass,
        "identity_matches": clause_pass[0],
        "version_matches": clause_pass[1],
        "length_matches": clause_pass[2],
        "unit_matches": clause_pass[3],
        "range_matches": clause_pass[4],
        "receiver_assumed_range_matches": visible_assumed_range_matches,
        "sequence_matches": clause_pass[5],
        "quality_encoding_matches": clause_pass[6],
        "checksum_matches": clause_pass[7],
        "cancellation": cancellation,
        "timeout": timeout,
        "event_observed": event_observed,
        "tie_resolved_to_cancellation": event_mode == "cancellation-timeout-tie",
        "transfer_attempted": transfer_attempted,
        "payload_arrived": transfer_attempted,
        "transmitted_id": transmitted_id,
        "payload_value": payload_value,
        "payload_unit": payload_unit,
        "transmitted_sequence": transmitted_sequence,
        "quality_code": quality_code,
        "checksum_expected": checksum_expected,
        "transmitted_checksum": transmitted_checksum,
        "contract_conformant": conformant,
        "receiver_value_plausible": value_plausible,
        "receiver_accepted": receiver_accepted,
        "receiver_released": receiver_released,
        "contract_eligible": contract_eligible,
        "false_acceptance": false_acceptance,
        "false_release": false_release,
        "receiver_decision_correct": receiver_decision_correct,
        "p06_angle": p06_angle,
        "semantic_error": semantic_error,
        "semantic_preserved": semantic_preserved,
        "p07_quality_preserved": p07_quality_preserved,
        "p06_scalar_contract_met": p06_scalar_contract_met,
        "range_margin": (
            180 - abs(payload_value)
            if transfer_attempted and payload_unit == "deg"
            else math.nan
        ),
        "receiver_assumed_range_margin": (
            180 - abs(payload_value) if transfer_attempted else math.nan
        ),
        "terminal": terminal,
        "failure": failure,
        "reporting_failure": reporting_failure,
    }


def assert_oracle_invariants(test: unittest.TestCase, result: dict[str, object]) -> None:
    test.assertEqual(result["event_observed"], result["cancellation"] or result["timeout"])
    test.assertEqual(result["transfer_attempted"], not result["event_observed"])
    test.assertEqual(result["payload_arrived"], result["transfer_attempted"])
    if result["transfer_attempted"]:
        test.assertTrue(all(result["clause_evaluated"]))
        test.assertEqual(
            result["clause_pass"],
            [
                result["identity_matches"],
                result["version_matches"],
                result["length_matches"],
                result["unit_matches"],
                result["range_matches"],
                result["sequence_matches"],
                result["quality_encoding_matches"],
                result["checksum_matches"],
            ],
        )
        test.assertTrue(math.isfinite(result["receiver_assumed_range_margin"]))
    else:
        test.assertFalse(any(result["clause_evaluated"]))
        test.assertFalse(any(result["clause_pass"]))
        for name in (
            "identity_matches",
            "version_matches",
            "length_matches",
            "unit_matches",
            "range_matches",
            "receiver_assumed_range_matches",
            "sequence_matches",
            "quality_encoding_matches",
            "checksum_matches",
        ):
            test.assertFalse(result[name])
        test.assertTrue(math.isnan(result["range_margin"]))
        test.assertTrue(math.isnan(result["receiver_assumed_range_margin"]))
    test.assertEqual(
        result["contract_conformant"],
        result["transfer_attempted"] and all(result["clause_pass"]),
    )
    test.assertEqual(
        result["contract_eligible"],
        result["contract_conformant"] and result["quality_code"] == 1,
    )
    test.assertEqual(
        result["false_acceptance"],
        result["receiver_accepted"] and not result["contract_conformant"],
    )
    test.assertEqual(
        result["false_release"],
        result["receiver_released"] and not result["contract_eligible"],
    )
    test.assertEqual(
        result["receiver_decision_correct"],
        result["transfer_attempted"]
        and result["receiver_accepted"] == result["contract_conformant"],
    )
    test.assertGreaterEqual(result["checksum_expected"], 0)
    test.assertLess(result["checksum_expected"], 65536)
    test.assertGreaterEqual(result["transmitted_checksum"], 0)
    test.assertLess(result["transmitted_checksum"], 65536)
    if result["transfer_attempted"] and result["unit_matches"]:
        test.assertEqual(
            result["range_margin"], result["receiver_assumed_range_margin"]
        )
    else:
        test.assertTrue(math.isnan(result["range_margin"]))
    if result["receiver_released"]:
        test.assertTrue(math.isfinite(result["p06_angle"]))
        test.assertEqual(result["p06_angle"], result["payload_value"])
        test.assertEqual(
            result["semantic_error"],
            result["p06_angle"] - result["source_angle"],
        )
    else:
        test.assertTrue(math.isnan(result["p06_angle"]))
        test.assertTrue(math.isnan(result["semantic_error"]))


class P08ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
        )
        cls.module = next(item for item in cls.manifest["modules"] if item["id"] == "P08")

    def read(self, name: str) -> str:
        return (P08 / name).read_text(encoding="utf-8")

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
                "number": 8,
                "id": "P08",
                "title": "Write an Interface Control Contract",
                "guiding_question": QUESTION,
                "phase": 2,
                "phase_title": "Allocation and interfaces",
                "slug": "write-an-interface-control-contract",
                "folder": "modules/08-write-an-interface-control-contract",
                "implementation_batch": "P08",
                "prerequisites": ["P07"],
            },
        )
        prerequisite = next(
            item for item in self.manifest["modules"] if item["id"] == "P07"
        )
        self.assertEqual(prerequisite["status"], "implemented")
        self.assertEqual(self.module["status"], "implemented")
        self.assertEqual(self.module["evidence_level"], "simulated")
        self.assertTrue(
            REQUIRED_ARTIFACTS <= {path.name for path in P08.iterdir() if path.is_file()}
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
        for marker in (
            "contractInterfaceId = 801",
            "contractVersion = 1",
            "requiredPayloadWords = 6",
            "minimumAngleDeg = -180",
            "maximumAngleDeg = 180",
            "maximumPayloadWords = 16",
            "maximumVersion = 255",
            "maximumSequence = 65535",
            "checksumModulus = 65536",
            "envelopeMetadataCount = numel(envelopeMetadataNames)",
        ):
            self.assertIn(marker, model)
        for fragment in (
            "checksumExpected=mod(transmittedInterfaceId+senderVersion+payloadWordCount+transmittedSequence+round(1000*payloadAngleValue)+wireQualityCode+unitCode,checksumModulus);",
            "cancellationObserved=any(strcmp(eventMode,{'cancellation','cancellation-timeout-tie'}));",
            "timeoutObserved=any(strcmp(eventMode,{'timeout','cancellation-timeout-tie'}));",
            "transferAttempted=~eventObserved;",
            "candidateIdentityMatches=transmittedInterfaceId==contractInterfaceId;",
            "candidateVersionMatches=senderVersion==contractVersion;",
            "candidateLengthMatches=payloadWordCount==requiredPayloadWords;",
            "candidateUnitMatches=strcmp(payloadUnit,expectedUnit);",
            "candidateReceiverAssumedRangeMatches=payloadAngleValue>=minimumAngleDeg&&payloadAngleValue<=maximumAngleDeg;",
            "candidateRangeMatches=candidateUnitMatches&&candidateReceiverAssumedRangeMatches;",
            "candidateSequenceMatches=transmittedSequence>=minimumSequence&&transmittedSequence<=maximumSequence&&transmittedSequence==round(transmittedSequence);",
            "candidateQualityEncodingMatches=wireQualityCode==0||wireQualityCode==1;",
            "candidateChecksumMatches=transmittedChecksum==checksumExpected;",
            "clausePass=candidateClausePass;",
            "contractConformant=transferAttempted&&all(clausePass);",
            "receiverValuePlausible=transferAttempted&&isfinite(payloadAngleValue)&&receiverAssumedRangeMatches;",
            "receiverAccepted=contractConformant;",
            "receiverAccepted=receiverValuePlausible;",
            "contractInputEligible=contractConformant&&wireQualityCode==1;",
            "falseAcceptance=receiverAccepted&&~contractConformant;",
            "falseRelease=receiverInputReleased&&~contractInputEligible;",
            "receiverDecisionCorrect=transferAttempted&&(receiverAccepted==contractConformant);",
            "p06ObservedAngleDeg=payloadAngleValue;",
            "normalized=double(value);",
            "ifnormalized<lowerBound||normalized>upperBound",
            "ifnormalized~=round(normalized)",
            "isfinite(value)&&(value==0||value==1)",
        ):
            self.assertIn(fragment, compact)
        self.assertNotIn("out.rawClausePass", model)
        self.assertLess(
            model.index("if cancellationObserved"),
            model.index("elseif timeoutObserved"),
        )
        for error_id in (
            "P08:InvalidAngle",
            "P08:InvalidPayloadWordCount",
            "P08:InvalidSenderVersion",
            "P08:InvalidSequence",
            "P08:InvalidQuality",
            "P08:InvalidFaultMode",
            "P08:InvalidEventMode",
            "P08:InvalidValidationMode",
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
            "crc",
            "hash(",
            "java.",
            "intlinprog(",
            "fmincon(",
        ):
            self.assertNotIn(forbidden, model.lower())

        all_matlab = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(P08.glob("*.m"))
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
            "intlinprog(",
            "optimproblem(",
            "fmincon(",
            "ga(",
            "system(",
            "unix(",
            "dos(",
        ):
            self.assertNotIn(opaque_or_external, all_matlab)

    def test_independent_oracle_baseline_and_record_equation(self):
        baseline = reference_contract()
        assert_oracle_invariants(self, baseline)
        self.assertEqual(baseline["checksum_expected"], 30874)
        self.assertEqual(baseline["transmitted_checksum"], 30874)
        self.assertTrue(all(baseline["clause_pass"]))
        self.assertTrue(baseline["contract_conformant"])
        self.assertTrue(baseline["receiver_accepted"])
        self.assertTrue(baseline["contract_eligible"])
        self.assertTrue(baseline["receiver_released"])
        self.assertEqual(baseline["p06_angle"], 30.021978021978)
        self.assertEqual(baseline["semantic_error"], 0)
        self.assertTrue(baseline["semantic_preserved"])
        self.assertTrue(baseline["p07_quality_preserved"])
        self.assertTrue(baseline["p06_scalar_contract_met"])
        self.assertEqual(baseline["terminal"], "accepted-and-released")
        self.assertEqual(baseline["failure"], "none")

    def test_independent_oracle_angle_sweep_and_inclusive_limits(self):
        angles = [-360, -180.001, -180, -90, 0, 30.021978021978, 180, 180.001, 360]
        results = [reference_contract(source_angle=angle) for angle in angles]
        for result in results:
            assert_oracle_invariants(self, result)
        self.assertEqual(
            [result["contract_conformant"] for result in results],
            [False, False, True, True, True, True, True, False, False],
        )
        self.assertEqual(results[2]["range_margin"], 0)
        self.assertEqual(results[6]["range_margin"], 0)
        self.assertEqual(results[4]["range_margin"], 180)
        for result in (results[0], results[1], results[7], results[8]):
            self.assertEqual(result["terminal"], "rejected")
            self.assertEqual(result["failure"], "angle-out-of-range")
            self.assertFalse(result["receiver_released"])

    def test_independent_oracle_payload_sweep_and_resource_limits(self):
        results = [reference_contract(payload_words=words) for words in range(17)]
        self.assertEqual(
            [result["contract_conformant"] for result in results],
            [False] * 6 + [True] + [False] * 10,
        )
        self.assertEqual(
            [result["receiver_released"] for result in results],
            [False] * 6 + [True] + [False] * 10,
        )
        for words, result in enumerate(results):
            assert_oracle_invariants(self, result)
            if words != 6:
                self.assertEqual(result["failure"], "payload-length-mismatch")

    def test_independent_oracle_version_sequence_and_quality_semantics(self):
        versions = [reference_contract(sender_version=version) for version in (0, 1, 2, 255)]
        self.assertEqual(
            [result["contract_conformant"] for result in versions],
            [False, True, False, False],
        )
        for result in versions:
            assert_oracle_invariants(self, result)
        minimum_sequence = reference_contract(sequence=0)
        maximum_sequence = reference_contract(sequence=65535)
        overflow = reference_contract(fault_mode="sequence-out-of-range")
        self.assertTrue(minimum_sequence["contract_conformant"])
        self.assertTrue(maximum_sequence["contract_conformant"])
        self.assertEqual(overflow["transmitted_sequence"], 65536)
        self.assertEqual(overflow["failure"], "sequence-out-of-range")

        invalid_quality = reference_contract(source_quality=False)
        assert_oracle_invariants(self, invalid_quality)
        self.assertTrue(invalid_quality["contract_conformant"])
        self.assertTrue(invalid_quality["receiver_accepted"])
        self.assertFalse(invalid_quality["contract_eligible"])
        self.assertFalse(invalid_quality["receiver_released"])
        self.assertEqual(invalid_quality["terminal"], "accepted-quality-withheld")
        self.assertEqual(invalid_quality["failure"], "source-quality-invalid")

    def test_independent_oracle_all_clause_faults_and_checksum_corruption(self):
        scenarios = {
            "identifier-mismatch": "identifier-mismatch",
            "unit-mismatch": "unit-mismatch",
            "sequence-out-of-range": "sequence-out-of-range",
            "quality-code-invalid": "quality-code-invalid",
            "checksum-corruption": "checksum-mismatch",
        }
        for fault, failure in scenarios.items():
            with self.subTest(fault=fault):
                result = reference_contract(fault_mode=fault)
                assert_oracle_invariants(self, result)
                self.assertFalse(result["contract_conformant"])
                self.assertFalse(result["receiver_accepted"])
                self.assertFalse(result["receiver_released"])
                self.assertEqual(result["terminal"], "rejected")
                self.assertEqual(result["failure"], failure)
        corrupted = reference_contract(fault_mode="checksum-corruption")
        self.assertEqual(
            corrupted["transmitted_checksum"],
            (corrupted["checksum_expected"] + 1) % 65536,
        )
        wrong_unit = reference_contract(fault_mode="unit-mismatch")
        self.assertEqual(wrong_unit["payload_unit"], "rad")
        self.assertFalse(wrong_unit["unit_matches"])
        self.assertFalse(wrong_unit["range_matches"])
        self.assertTrue(wrong_unit["receiver_assumed_range_matches"])
        self.assertTrue(math.isnan(wrong_unit["range_margin"]))
        self.assertGreater(wrong_unit["receiver_assumed_range_margin"], 179)
        self.assertAlmostEqual(
            wrong_unit["payload_value"], 30.021978021978 * math.pi / 180
        )

    def test_independent_oracle_cancellation_timeout_and_event_isolation(self):
        cancelled = reference_contract(event_mode="cancellation")
        timed_out = reference_contract(event_mode="timeout")
        tied = reference_contract(event_mode="cancellation-timeout-tie")
        timeout_over_mismatch = reference_contract(
            payload_words=5,
            sender_version=0,
            fault_mode="checksum-corruption",
            event_mode="timeout",
        )
        for result in (cancelled, timed_out, tied, timeout_over_mismatch):
            assert_oracle_invariants(self, result)
            self.assertTrue(result["event_observed"])
            self.assertFalse(result["transfer_attempted"])
            self.assertFalse(result["payload_arrived"])
            self.assertFalse(any(result["clause_evaluated"]))
            self.assertFalse(result["receiver_accepted"])
            self.assertFalse(result["receiver_decision_correct"])
            self.assertFalse(result["receiver_released"])
        self.assertEqual(cancelled["terminal"], "cancelled")
        self.assertEqual(cancelled["failure"], "transfer-cancelled")
        self.assertEqual(timed_out["terminal"], "timed-out")
        self.assertEqual(timed_out["failure"], "transfer-timeout")
        self.assertTrue(tied["tie_resolved_to_cancellation"])
        self.assertEqual(tied["terminal"], "cancelled")
        self.assertEqual(timeout_over_mismatch["failure"], "transfer-timeout")

    def test_independent_oracle_broken_validation_false_acceptance_and_release(self):
        strict_unit = reference_contract(fault_mode="unit-mismatch")
        broken_unit = reference_contract(
            fault_mode="unit-mismatch", validation_mode="value-only"
        )
        for factual_key in (
            "clause_evaluated",
            "clause_pass",
            "payload_arrived",
            "payload_value",
            "payload_unit",
            "transmitted_checksum",
            "contract_conformant",
            "failure",
        ):
            self.assertEqual(strict_unit[factual_key], broken_unit[factual_key])
        self.assertFalse(strict_unit["receiver_accepted"])
        self.assertTrue(broken_unit["receiver_accepted"])
        self.assertTrue(broken_unit["receiver_released"])
        self.assertTrue(broken_unit["false_acceptance"])
        self.assertTrue(broken_unit["false_release"])
        self.assertFalse(broken_unit["receiver_decision_correct"])
        self.assertFalse(broken_unit["semantic_preserved"])
        self.assertAlmostEqual(
            broken_unit["semantic_error"],
            30.021978021978 * math.pi / 180 - 30.021978021978,
        )
        self.assertEqual(
            broken_unit["reporting_failure"], "value-only-false-acceptance"
        )

        broken_quality = reference_contract(
            source_quality=False, validation_mode="value-only"
        )
        self.assertTrue(broken_quality["contract_conformant"])
        self.assertTrue(broken_quality["receiver_accepted"])
        self.assertTrue(broken_quality["receiver_released"])
        self.assertFalse(broken_quality["contract_eligible"])
        self.assertFalse(broken_quality["false_acceptance"])
        self.assertTrue(broken_quality["false_release"])
        self.assertEqual(
            broken_quality["reporting_failure"], "value-only-false-release"
        )
        out_of_range = reference_contract(
            source_angle=180.001, validation_mode="value-only"
        )
        self.assertFalse(out_of_range["receiver_value_plausible"])
        self.assertFalse(out_of_range["receiver_accepted"])
        self.assertFalse(out_of_range["false_acceptance"])

    def test_value_only_ignores_every_non_value_clause_behaviorally(self):
        scenarios = {
            "identity": {"fault_mode": "identifier-mismatch"},
            "version": {"sender_version": 2},
            "payload length": {"payload_words": 5},
            "unit": {"fault_mode": "unit-mismatch"},
            "sequence": {"fault_mode": "sequence-out-of-range"},
            "quality encoding": {"fault_mode": "quality-code-invalid"},
            "checksum": {"fault_mode": "checksum-corruption"},
        }
        for clause, inputs in scenarios.items():
            with self.subTest(clause=clause):
                strict = reference_contract(**inputs)
                broken = reference_contract(validation_mode="value-only", **inputs)
                assert_oracle_invariants(self, strict)
                assert_oracle_invariants(self, broken)
                for factual_key in (
                    "clause_evaluated",
                    "clause_pass",
                    "payload_arrived",
                    "payload_value",
                    "payload_unit",
                    "transmitted_sequence",
                    "transmitted_checksum",
                    "contract_conformant",
                    "failure",
                ):
                    self.assertEqual(strict[factual_key], broken[factual_key])
                self.assertFalse(strict["contract_conformant"])
                self.assertFalse(strict["receiver_accepted"])
                self.assertTrue(broken["receiver_value_plausible"])
                self.assertTrue(broken["receiver_accepted"])
                self.assertTrue(broken["receiver_released"])
                self.assertTrue(broken["false_acceptance"])
                self.assertTrue(broken["false_release"])
                self.assertFalse(broken["receiver_decision_correct"])
                self.assertEqual(
                    broken["reporting_failure"],
                    "value-only-false-acceptance",
                )

        checks = self.read("run_checks.m")
        for marker in (
            "brokenIdentity = model",
            "brokenVersion = model",
            "brokenLength = model",
            "brokenUnit = model",
            "brokenSequence = model",
            "brokenQualityEncoding = model",
            "brokenChecksum = model",
        ):
            self.assertIn(marker, checks)

    def test_every_supported_terminal_is_behaviorally_reachable(self):
        scenarios = [
            reference_contract(),
            reference_contract(source_quality=False),
            reference_contract(source_angle=180.001),
            reference_contract(event_mode="cancellation"),
            reference_contract(event_mode="timeout"),
        ]
        self.assertEqual(
            {scenario["terminal"] for scenario in scenarios},
            {
                "accepted-and-released",
                "accepted-quality-withheld",
                "rejected",
                "cancelled",
                "timed-out",
            },
        )

    def test_experiment_has_ordered_baselines_two_sweeps_and_broken_case(self):
        experiment = self.read("experiment.m")
        sweep_sections = re.findall(r"^%% Sweep [12].*$", experiment, flags=re.MULTILINE)
        self.assertEqual(len(sweep_sections), 2)
        for marker in (
            "sourceAngleSweepDeg = [-180 -90 0 30.021978021978 180 180.001]",
            "payloadWordSweep = [4 5 6 7 8]",
            "isequal(conformantByAngle,[true true true true true false])",
            "isequal(lengthClauseByWords,[false false true false false])",
            "versionBelow",
            "versionAbove",
            "checksum-corruption",
            "qualityWithheld",
            "cancellation-timeout-tie",
            "unit-mismatch",
            "value-only",
            "broken.falseAcceptance",
            "broken.falseRelease",
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
        for unit in ("(deg)", " word", " count", "Boolean -"):
            self.assertIn(unit, experiment)
        self.assertIn("not transfer duration", experiment)
        self.assertIn("no milliseconds", experiment)

    def test_interactive_controls_are_bounded_meaningful_and_resettable(self):
        interactive = self.read("interactive.m")
        self.assertIn("modelFcn = @model", interactive)
        self.assertIn("out = modelFcn(", interactive)
        self.assertGreaterEqual(interactive.count("uispinner"), 4)
        self.assertGreaterEqual(interactive.count("uidropdown"), 3)
        self.assertIn("uicheckbox", interactive)
        self.assertGreaterEqual(interactive.count("ValueChangedFcn"), 8)
        for limits in (
            "'Limits',[-360 360]",
            "'Limits',[0 16]",
            "'Limits',[0 255]",
            "'Limits',[0 65535]",
        ):
            self.assertIn(limits, interactive)
        self.assertIn("faultMode.ItemsData", interactive)
        self.assertIn("eventMode.ItemsData", interactive)
        self.assertIn("cancellation-timeout-tie", interactive)
        self.assertIn("validationMode.ItemsData = {'complete','value-only'}", interactive)
        self.assertIn("resetBaseline", interactive)
        for marker in (
            "sourceAngle.Value = 30.021978021978",
            "payloadWords.Value = 6",
            "senderVersion.Value = 1",
            "sequenceNumber.Value = 42",
            "sourceQuality.Value = true",
            "faultMode.Value = 'none'",
            "eventMode.Value = 'none'",
            "validationMode.Value = 'complete'",
        ):
            self.assertIn(marker, interactive)
        self.assertIn("Clause result (Boolean -)", interactive)
        self.assertIn("Position interpreted as degrees (deg)", interactive)
        self.assertIn("false acceptance", interactive)
        self.assertIn("semantic error", interactive)

    def test_checks_cover_failures_recovery_compatibility_and_bounds(self):
        checks = self.read("run_checks.m")
        for marker in (
            "expectedClauseNames",
            "expectedPayloadFieldNames",
            "expectedPayloadFieldUnits",
            "expectedEnvelopeMetadataNames",
            "expectedEnvelopeMetadataUnits",
            "independentChecksum",
            "negativeLimit",
            "positiveLimit",
            "negativeJustOutside",
            "positiveJustOutside",
            "negativeMaximum",
            "positiveMaximum",
            "payloadWordChoices = 0:16",
            "minimumPayload",
            "maximumPayload",
            "minimumVersion",
            "supportedVersion",
            "nextVersion",
            "maximumVersion",
            "minimumSequence",
            "maximumSequence",
            "sequenceOutOfRange",
            "wrongIdentity",
            "wrongUnit",
            "invalidQualityCode",
            "corruptedChecksum",
            "qualityWithheld",
            "cancelled",
            "timedOut",
            "tied",
            "eventBeforeMismatch",
            "brokenIdentity",
            "brokenUnit",
            "brokenVersion",
            "brokenLength",
            "brokenSequence",
            "brokenChecksum",
            "brokenQualityEncoding",
            "brokenQuality",
            "brokenOutOfRange",
            "string(' NONE ')",
            "P08:InvalidAngle",
            "P08:InvalidPayloadWordCount",
            "P08:InvalidSenderVersion",
            "P08:InvalidSequence",
            "P08:InvalidQuality",
            "P08:InvalidFaultMode",
            "P08:InvalidEventMode",
            "P08:InvalidValidationMode",
            "afterMalformed",
            "assertContractInvariant",
            "P08 checks passed",
        ):
            self.assertIn(marker, checks)

    def test_lesson_is_concept_first_compounds_and_preserves_boundaries(self):
        combined = "\n".join(
            self.read(name)
            for name in ("README.md", "lesson.m", "lesson.md", "walkthrough.md", "checks.md")
        )
        self.assertGreaterEqual(combined.count(QUESTION), 3)
        for marker in (
            "P06",
            "P07",
            "P09",
            "P11",
            "P12",
            "P13",
            "P20",
            "producer",
            "receiver",
            "identity",
            "version",
            "payload",
            "unit",
            "range",
            "sequence",
            "quality",
            "checksum",
            "input",
            "observable",
            "failure",
            "cancellation",
            "timeout",
            "recovery",
            "interpretation",
            "teach-back",
        ):
            self.assertIn(marker.lower(), combined.lower())
        flattened = re.sub(r"\s+", " ", combined)
        self.assertIn("does not add an argument to P06 or rewrite P07", flattened)
        self.assertIn("not a recommended production checksum", flattened)
        self.assertIn("not P06 execution", flattened)
        self.assertLessEqual(self.read("lesson.m").lower().count("prediction:"), 1)

    def test_p06_and_p07_compatibility_remain_scalar_and_quality_gated(self):
        p06_model = (ROOT / "modules/06-trace-a-command-path/model.m").read_text(
            encoding="utf-8"
        )
        p07_model = (ROOT / "modules/07-trace-a-measurement-data-path/model.m").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            p06_model,
            r"function out = model\(requestedAngleDeg,observedAngleDeg,",
        )
        self.assertNotIn("qualityValid", p06_model)
        self.assertRegex(
            p07_model,
            r"function out = model\(trueAngleDeg,adcBits,sampleAgeMs,",
        )
        self.assertIn("p06InputEligible = measurementUsable", p07_model)
        self.assertIn("p06ObservedAngleDeg = stageOutputValue(5)", p07_model)

        combined = "\n".join(
            self.read(name) for name in ("README.md", "lesson.m", "lesson.md", "checks.md")
        )
        for marker in (
            "P07's gate",
            "P06's scalar",
            "observedAngleDeg",
            "does not add an argument to P06 or rewrite P07",
        ):
            self.assertIn(marker, combined)
        self.assertNotIn("run_module_checks", self.read("model.m"))

    def test_rollback_fixture_recovers_persisted_p08_to_p07_without_erasure(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(ROOT / "bin", fixture / "bin")
            (fixture / "curriculum").mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "curriculum/modules.json").read_text(encoding="utf-8")
            )
            for module in manifest["modules"]:
                if module["number"] >= 8:
                    module["status"] = "scaffolded"
                    module["evidence_level"] = "none"
            (fixture / "curriculum/modules.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            retained_note = "P08 Interface Control Contract teach-back retained"
            (state_dir / "progress.json").write_text(
                json.dumps(
                    {
                        "current": "P08",
                        "completed": {"P08": True},
                        "notes": {"P08": retained_note},
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
            self.assertIn("P07 — Trace a Measurement Data Path", recovered.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("24 total, 7 implemented, 0 completed", status.stdout)
            self.assertEqual(listing.returncode, 0, listing.stderr)
            p08_line = next(line for line in listing.stdout.splitlines() if " P08 " in line)
            self.assertTrue(p08_line.startswith("○ P08"), p08_line)
            self.assertNotIn("✓ P08", listing.stdout)
            state = json.loads(
                (state_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], "P07")
            self.assertTrue(state["completed"]["P08"])
            self.assertEqual(state["notes"]["P08"], retained_note)

    def test_retained_evidence_has_required_sections_and_claim_boundary(self):
        evidence_files = sorted((ROOT / "docs/evidence").glob("P08-*.md"))
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
