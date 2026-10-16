import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loop"))
import controller  # noqa: E402


def write_contract(d: Path, **over) -> Path:
    c = {
        "goal": "test",
        "worker": [sys.executable, "-c", "pass"],
        "checks": [[sys.executable, "-c", "pass"]],
        "allowed_paths": ["src/"],
        "max_iterations": 3,
        "retry_budget": 2,
        "time_limit_sec": 60,
    }
    c.update(over)
    p = d / "contract.json"
    p.write_text(json.dumps(c), encoding="utf-8")
    return p


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        (self.work / "src").mkdir(parents=True)
        self.state = self.root / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def test_passes_on_first_iteration(self):
        cpath = write_contract(self.root)
        st = controller.run(cpath, self.work, self.state)
        self.assertEqual(st.status, "passed")
        self.assertEqual(st.iteration, 1)

    def test_halts_after_retry_budget(self):
        cpath = write_contract(self.root, worker=[sys.executable, "-c", "import sys; sys.exit(1)"])
        st = controller.run(cpath, self.work, self.state)
        self.assertEqual(st.status, "halted_budget")
        self.assertEqual(st.consecutive_failures, 2)

    def test_worker_change_outside_allowed_path_fails(self):
        cpath = write_contract(
            self.root,
            worker=[sys.executable, "-c", "open('forbidden.txt','w').write('x')"],
            max_iterations=1,
            retry_budget=1,
        )
        st = controller.run(cpath, self.work, self.state)
        self.assertEqual(st.status, "halted_budget")
        self.assertIn("forbidden.txt", st.history[0]["violations"])

    def test_resume_does_not_rerun_finished_state(self):
        cpath = write_contract(self.root)
        controller.run(cpath, self.work, self.state)
        st = controller.run(cpath, self.work, self.state)
        self.assertEqual(st.status, "passed")
        self.assertEqual(st.iteration, 1)

    def test_invalid_contract_rejected(self):
        cpath = write_contract(self.root, retry_budget=0)
        with self.assertRaises(ValueError):
            controller.load_contract(cpath)

    def test_missing_command_is_failure_not_crash(self):
        cpath = write_contract(self.root, worker=["definitely-not-a-real-command-xyz"], max_iterations=1, retry_budget=1)
        st = controller.run(cpath, self.work, self.state)
        self.assertEqual(st.status, "halted_budget")


if __name__ == "__main__":
    unittest.main()
