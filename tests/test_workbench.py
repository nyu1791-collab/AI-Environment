import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "ai_env.py"
SPEC = importlib.util.spec_from_file_location("ai_env", MODULE_PATH)
ai_env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ai_env)


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = ai_env.connect(Path(self.temp.name) / "workbench.sqlite3")
        self.project = ai_env.add_project(self.db, "動画以外の企画", "顧客の作業を減らす")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_project_and_task_round_trip(self):
        task = ai_env.add_task(self.db, self.project, "要件整理", "要件一覧がある", "設計")
        ai_env.change_status(self.db, self.project, task, "in_progress")
        report = ai_env.export_project(self.db, self.project)
        self.assertIn("# 動画以外の企画", report)
        self.assertIn("要件一覧がある", report)
        self.assertIn("In Progress: 1", report)

    def test_invalid_transition_is_rejected(self):
        task = ai_env.add_task(self.db, self.project, "作業", "成果物がある", "")
        ai_env.change_status(self.db, self.project, task, "in_progress")
        ai_env.change_status(self.db, self.project, task, "done")
        with self.assertRaisesRegex(ValueError, "cannot change"):
            ai_env.change_status(self.db, self.project, task, "todo")

    def test_unknown_project_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown project"):
            ai_env.add_task(self.db, "missing", "作業", "確認", "owner")

    def test_duplicate_project_does_not_overwrite(self):
        with self.assertRaises(sqlite3.IntegrityError):
            ai_env.add_project(self.db, "動画以外の企画", "different goal")
        self.assertEqual(
            self.db.execute("SELECT objective FROM projects WHERE id=?", (self.project,)).fetchone()[0],
            "顧客の作業を減らす",
        )

    def test_markdown_export_is_repeatable(self):
        ai_env.add_task(self.db, self.project, "同じ出力", "同じ結果", "qa")
        self.assertEqual(
            ai_env.export_project(self.db, self.project),
            ai_env.export_project(self.db, self.project),
        )


if __name__ == "__main__":
    unittest.main()
