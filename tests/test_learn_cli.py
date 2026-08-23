from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LearnCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "curriculum/modules.json").read_text(encoding="utf-8"))

    def make_fixture(self, parent: Path) -> Path:
        fixture = parent / "repo"
        shutil.copytree(ROOT / "bin", fixture / "bin")
        shutil.copytree(ROOT / "curriculum", fixture / "curriculum")
        for module in self.manifest["modules"]:
            source = ROOT / module["folder"]
            target = fixture / module["folder"]
            target.mkdir(parents=True, exist_ok=True)
            for name in ("README.md", "lesson.md", "walkthrough.md", "checks.md"):
                shutil.copy2(source / name, target / name)
        return fixture

    def invoke(self, fixture: Path, *args: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [str(fixture / "bin/learn"), *args],
            cwd=fixture,
            text=True,
            capture_output=True,
            env=environment,
            timeout=10,
        )

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            return self.invoke(fixture, *args)

    def test_status_and_list_derive_the_current_frontier(self):
        implemented = sum(
            module["status"] == "implemented" for module in self.manifest["modules"]
        )
        status = self.run_cli("status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn(
            f"{self.manifest['module_count']} total, {implemented} implemented",
            status.stdout,
        )
        listing = self.run_cli("list")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(
            len([line for line in listing.stdout.splitlines() if line.strip()]),
            self.manifest["module_count"],
        )

    def test_every_implemented_module_starts_and_first_scaffold_refuses(self):
        for module in self.manifest["modules"]:
            if module["status"] != "implemented":
                continue
            with self.subTest(module=module["id"]):
                started = self.run_cli("start", module["id"])
                self.assertEqual(started.returncode, 0, started.stderr)
                self.assertIn(f"Guiding question: {module['guiding_question']}", started.stdout)

        scaffold = next(
            (module for module in self.manifest["modules"] if module["status"] == "scaffolded"),
            None,
        )
        if scaffold is not None:
            refused = self.run_cli("start", scaffold["id"])
            self.assertEqual(refused.returncode, 2)
            self.assertIn("Activate its governed implementation batch", refused.stdout)

    def test_refused_scaffold_does_not_replace_current_module(self):
        implemented = [
            module for module in self.manifest["modules"] if module["status"] == "implemented"
        ]
        scaffold = next(
            (module for module in self.manifest["modules"] if module["status"] == "scaffolded"),
            None,
        )
        if not implemented or scaffold is None:
            self.skipTest("Recovery needs both an implemented module and a remaining scaffold.")

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            current = implemented[-1]
            started = self.invoke(fixture, "start", current["id"])
            self.assertEqual(started.returncode, 0, started.stderr)
            refused = self.invoke(fixture, "start", scaffold["id"])
            self.assertEqual(refused.returncode, 2)
            resumed = self.invoke(fixture, "continue")
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn(f"{current['id']} — {current['title']}", resumed.stdout)
            state = json.loads(
                (fixture / ".learning/progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["current"], current["id"])

    def test_continue_without_state_preserves_the_default_first_lesson(self):
        first_implemented = next(
            module for module in self.manifest["modules"] if module["status"] == "implemented"
        )
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            resumed = self.invoke(fixture, "continue")
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn(
                f"{first_implemented['id']} — {first_implemented['title']}", resumed.stdout
            )
            self.assertFalse((fixture / ".learning/progress.json").exists())

    def test_continue_recovers_from_unknown_or_rolled_back_current(self):
        implemented = [
            module for module in self.manifest["modules"] if module["status"] == "implemented"
        ]
        self.assertTrue(implemented)
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            state_dir = fixture / ".learning"
            state_dir.mkdir()
            state_path = state_dir / "progress.json"
            state_path.write_text(
                json.dumps({"current": "P99", "completed": {}, "notes": {}}) + "\n",
                encoding="utf-8",
            )
            resumed = self.invoke(fixture, "continue")
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn(f"{implemented[-1]['id']} —", resumed.stdout)

            fixture_manifest_path = fixture / "curriculum/modules.json"
            fixture_manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
            fixture_manifest["modules"][len(implemented) - 1]["status"] = "scaffolded"
            fixture_manifest_path.write_text(
                json.dumps(fixture_manifest, indent=2) + "\n", encoding="utf-8"
            )
            state_path.write_text(
                json.dumps(
                    {"current": implemented[-1]["id"], "completed": {}, "notes": {}}
                )
                + "\n",
                encoding="utf-8",
            )
            recovered = self.invoke(fixture, "continue")
            if len(implemented) > 1:
                self.assertEqual(recovered.returncode, 0, recovered.stderr)
                self.assertIn(f"{implemented[-2]['id']} —", recovered.stdout)
            else:
                self.assertNotEqual(recovered.returncode, 0)

    def test_unknown_module_is_rejected_without_persisting_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            rejected = self.invoke(fixture, "start", "not-a-module")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Unknown module", rejected.stderr)
            self.assertFalse((fixture / ".learning/progress.json").exists())


if __name__ == "__main__":
    unittest.main()
