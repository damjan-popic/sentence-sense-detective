from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_common import read_jsonl  # noqa: E402

REMAP_PATH = ROOT / "data/remap/en/pedagogical_candidates_10k.jsonl.gz"


class FormalRemapProvenanceTests(unittest.TestCase):
    def test_every_10k_candidate_is_traceable(self) -> None:
        required = {
            "remap_candidate_id",
            "remap_profile",
            "remap_profile_sha256",
            "remap_rule_id",
            "decision_class",
            "action",
            "source_case_ids",
            "matched_evidence",
            "stanza_version",
            "model_bundle_sha256",
        }
        count = 0
        for item in read_jsonl(REMAP_PATH):
            count += 1
            self.assertFalse(required - set(item))
            self.assertTrue(item["source_case_ids"])
            self.assertTrue(item["matched_evidence"]["token_ids"])
            self.assertEqual("1.14.0", item["stanza_version"])
            self.assertTrue(item["model_bundle_sha256"])
        self.assertEqual(274_198, count)


if __name__ == "__main__":
    unittest.main()
