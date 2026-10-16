import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loop"))
import ledger  # noqa: E402
import review  # noqa: E402


class LedgerTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ledger.jsonl"
            ledger.append(p, {"agent": "a", "event": "start"})
            ledger.append(p, {"agent": "a", "event": "done"})
            self.assertEqual(ledger.verify(p), (True, 2))
            text = p.read_text(encoding="utf-8").replace('"done"', '"edited"')
            p.write_text(text, encoding="utf-8")
            ok, _ = ledger.verify(p)
            self.assertFalse(ok)

    def test_empty_ledger_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(ledger.verify(Path(d) / "none.jsonl"), (True, 0))


class ReviewTests(unittest.TestCase):
    def test_summarize_counts_nonempty_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "glm-1").mkdir()
            (root / "glm-1" / "vote.md").write_text("A", encoding="utf-8")
            (root / "glm-2").mkdir()
            (root / "glm-2" / "proposal.md").write_text("", encoding="utf-8")
            rows = {r["agent"]: r for r in review.summarize(root)}
            self.assertEqual(rows["glm-1"]["vote.md"], 1)
            self.assertEqual(rows["glm-2"]["proposal.md"], 0)


if __name__ == "__main__":
    unittest.main()
