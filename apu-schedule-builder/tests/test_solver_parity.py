"""web/solver.js must produce exactly what app_backend.py produces.

The browser build runs the solver locally, so the JavaScript port is only safe
while it agrees with the Python reference. This test builds a config matrix,
runs both solvers over it and compares the full result payloads.

It needs Node and a normalized dataset. Both are optional, so the test skips
rather than fails when they are missing:

    py -3 build_site.py --colleges APM      # writes data/normalized/APM.json
    py -3 -m unittest tests.test_solver_parity -v

By default it checks a representative slice of the config matrix against one
dataset, which keeps the suite quick. The full sweep - every config against
every college - takes several minutes and runs on demand:

    APU_PARITY_FULL=1 py -3 -m unittest tests.test_solver_parity -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app

ROOT = Path(__file__).resolve().parents[1]
JS_RUNNER = ROOT / "tests" / "solver_parity_js.mjs"


def build_config_matrix(data: dict) -> list[dict]:
    """A spread of configs that exercises every branch the solver has."""
    subjects = [s["subjectCode"] for s in data["subjects"]]
    sections = data["sections"]
    semester_codes = [s["classCode"] for s in sections if s.get("term") == "SEMESTER"]
    quarter_codes = [s["classCode"] for s in sections if s.get("term") in {"Q1", "Q2"}]

    configs: list[dict] = []
    for target in (4, 10, 16, 20):
        configs.append({"semesterLevel": 5, "targetCredits": target, "autofill": True})
    for level in (1, 2, 3, 7, 8):
        configs.append({"semesterLevel": level, "targetCredits": 12, "autofill": True})

    configs += [
        {"semesterLevel": 5, "targetCredits": 18, "autofill": True, "accelerated": True, "maxCredits": 24},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "daysOff": ["FRI"]},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "daysOff": ["MON", "FRI"], "maxCampusDays": 3},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "earliestPeriod": 2, "latestPeriod": 4},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "maxGap": 0},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "preferredLanguages": ["E"]},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "preferredLanguages": ["J", "E"]},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": False},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": False, "statuses": {subjects[0]: "MUST"}},
        {
            "semesterLevel": 5,
            "targetCredits": 14,
            "autofill": True,
            "statuses": {subjects[0]: "MUST", subjects[1]: "PREFER", subjects[2]: "EXCLUDE"},
        },
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "fixedClassCodes": semester_codes[:1]},
        {"semesterLevel": 5, "targetCredits": 16, "autofill": True, "fixedClassCodes": semester_codes[:3]},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "fixedClassCodes": quarter_codes[:2]},
        {"semesterLevel": 5, "targetCredits": 12, "autofill": True, "fixedClassCodes": ["NOPE"]},
        {
            "semesterLevel": 5,
            "targetCredits": 12,
            "autofill": True,
            "blockedSlots": [f"Q1:{d}:{p}" for d in ("MON", "TUE") for p in (1, 2, 3)],
        },
        {
            "semesterLevel": 5,
            "targetCredits": 12,
            "autofill": True,
            "blockedSlots": ["Q1:MON:1", "bogus", "Q9:MON:1", "Q1:XXX:1", "Q1:MON:99"],
        },
        {
            "semesterLevel": 6,
            "targetCredits": 20,
            "autofill": True,
            "daysOff": ["WED"],
            "earliestPeriod": 2,
            "latestPeriod": 5,
            "maxGap": 1,
            "maxCampusDays": 4,
            "preferredLanguages": ["E"],
            "blockedSlots": ["Q2:FRI:5", "Q2:FRI:6"],
            "fixedClassCodes": semester_codes[:1],
        },
    ]
    return configs


def python_results(data: dict, configs: list[dict]) -> list[dict]:
    out = []
    for config in configs:
        result = app.generate_schedules(data, config)
        out.append({
            "errors": result["errors"],
            "results": [{
                "label": r["label"],
                "score": r["score"],
                "credits": r["credits"],
                "codes": sorted(str(c["classCode"]) for c in r["courses"]),
                "metrics": r["metrics"],
                "explanations": r["explanations"],
                "warnings": r["warnings"],
            } for r in result["results"]],
        })
    return out


class SolverParityTests(unittest.TestCase):
    def test_javascript_solver_matches_the_python_reference(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is not installed; cannot check the browser solver.")

        datasets = sorted((ROOT / "data" / "normalized").glob("*.json"))
        if not datasets:
            self.skipTest("No normalized dataset; run build_site.py first.")

        full = bool(os.environ.get("APU_PARITY_FULL"))
        if not full:
            datasets = datasets[:1]

        for dataset in datasets:
            with self.subTest(college=dataset.stem):
                data = json.loads(dataset.read_text(encoding="utf-8"))
                configs = build_config_matrix(data)
                if not full:
                    # Every third config still covers each solver branch.
                    configs = configs[::3]
                expected = python_results(data, configs)

                with tempfile.TemporaryDirectory() as tmp:
                    config_path = Path(tmp) / "configs.json"
                    config_path.write_text(json.dumps(configs), encoding="utf-8")
                    proc = subprocess.run(
                        [node, str(JS_RUNNER), str(dataset), str(config_path)],
                        capture_output=True, text=True, encoding="utf-8", timeout=600,
                    )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                actual = json.loads(proc.stdout)

                self.assertEqual(len(actual), len(expected))
                for i, (want, got) in enumerate(zip(expected, actual)):
                    self.assertEqual(got, want, f"config #{i} diverged: {json.dumps(configs[i])}")


if __name__ == "__main__":
    unittest.main()
