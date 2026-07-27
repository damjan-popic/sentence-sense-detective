from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_common import read_jsonl, write_jsonl  # noqa: E402


class PipelineCommonTests(unittest.TestCase):
    def test_gzip_jsonl_is_deterministic_and_round_trips(self) -> None:
        rows = [{"id": "one", "value": "č"}, {"id": "two", "value": 2}]
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.jsonl.gz"
            second = Path(temporary) / "second.jsonl.gz"
            write_jsonl(first, rows)
            write_jsonl(second, rows)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(list(read_jsonl(first)), rows)


if __name__ == "__main__":
    unittest.main()
