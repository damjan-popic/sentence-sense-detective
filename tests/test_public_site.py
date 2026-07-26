from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "docs/index.html").read_text(encoding="utf-8")
JS = (ROOT / "docs/assets/app.js").read_text(encoding="utf-8")
ROUND_STATE = (ROOT / "docs/assets/round-state.js").read_text(encoding="utf-8")
QUESTION_BANK = (ROOT / "docs/assets/question-bank.js").read_text(encoding="utf-8")
CSS = (ROOT / "docs/assets/styles.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "docs/data/en/manifest.json").read_text(encoding="utf-8"))


class PublicSiteTests(unittest.TestCase):
    def test_product_name_modes_and_counts(self) -> None:
        self.assertIn("Sentence Sense Detective", HTML)
        self.assertEqual(
            ["Parts of Speech", "Sentence Elements", "Clauses"],
            [mode["title"] for mode in MANIFEST["modes"]],
        )
        self.assertEqual(156, MANIFEST["totals"]["questions"])
        self.assertEqual(92, MANIFEST["totals"]["sentences"])

    def test_manifest_is_initial_payload_and_shards_are_lazy(self) -> None:
        self.assertNotIn("data/questions.js", HTML)
        self.assertNotIn("SENTENCE_SENSE_DATA", JS)
        self.assertIn("data/en/manifest.json", JS)
        self.assertIn("async function fetchShard", JS)
        self.assertIn("MAX_CACHED_SHARDS = 2", JS)
        self.assertIn("loadModeRound(button.dataset.mode)", JS)

    def test_public_shards_match_manifest_and_strip_internal_fields(self) -> None:
        public_fields = {
            "id", "sentence_id", "language", "mode", "subskill", "sentence",
            "target_spans", "prompt", "answer", "options", "explanation",
        }
        seen = set()
        for shard in MANIFEST["shards"]:
            path = ROOT / "docs/data/en" / shard["path"]
            content = path.read_bytes()
            self.assertEqual(shard["bytes"], len(content))
            self.assertEqual(shard["sha256"], hashlib.sha256(content).hexdigest())
            payload = json.loads(content)
            self.assertEqual(shard["count"], len(payload["questions"]))
            for question in payload["questions"]:
                self.assertEqual(public_fields, set(question))
                self.assertNotIn(question["id"], seen)
                seen.add(question["id"])
        self.assertEqual(156, len(seen))

    def test_brand_and_favicon_assets(self) -> None:
        assets = (
            "logo-mark.svg", "favicon.svg", "favicon-16x16.png",
            "favicon-32x32.png", "apple-touch-icon.png", "icon-192.png",
            "icon-512.png",
        )
        for asset in assets:
            self.assertTrue((ROOT / "docs/assets" / asset).is_file(), asset)
        self.assertTrue((ROOT / "docs/site.webmanifest").is_file())
        self.assertIn('src="assets/logo-mark.svg"', HTML)
        self.assertNotIn("🔎", HTML)

    def test_about_methodology_is_exact_and_version_is_dynamic(self) -> None:
        self.assertEqual(1, HTML.count("<!-- methodology-note:start -->"))
        self.assertEqual(1, HTML.count("<!-- methodology-note:end -->"))
        self.assertIn("The English pilot began with 106 examples", HTML)
        self.assertIn("Our next target is an open corpus of roughly 10,000", HTML)
        self.assertIn('id="about-version"', HTML)
        self.assertIn("els.aboutVersion.textContent = loaded.version", JS)

    def test_required_interactions_and_recoverable_loading_exist(self) -> None:
        for element_id in (
            "show-answer", "next-question", "review-mistakes", "score-value",
            "streak-value", "breakdown-list", "mistakes-list", "manifest-retry",
            "round-retry", "round-load-home", "report-question",
        ):
            self.assertIn(f'id="{element_id}"', HTML)
        self.assertIn("one more try", JS)
        self.assertIn("firstTryCorrect", JS)
        self.assertIn("SentenceSenseRound", JS)
        self.assertIn("SentenceSenseQuestionBank", JS)
        self.assertIn("retry-available", ROUND_STATE)
        self.assertIn("recent_history_limit", JS)
        self.assertIn("appendRecent", QUESTION_BANK)

    def test_accessibility_and_reduced_motion_contracts(self) -> None:
        self.assertIn('<main id="main" tabindex="-1">', HTML)
        self.assertIn('role="progressbar"', HTML)
        self.assertIn('aria-live="polite"', HTML)
        self.assertIn('id="question-card" class="question-card" tabindex="-1"', HTML)
        self.assertIn("focusWithoutScroll(els.questionCard)", JS)
        self.assertIn("focusWithoutScroll(els.summaryTitle)", JS)
        self.assertIn("@media (prefers-reduced-motion: reduce)", CSS)
        self.assertIn("return prefersReducedMotion() ? 'auto' : 'smooth';", JS)
        self.assertIn("if (prefersReducedMotion()) return;", JS)

    def test_report_link_prefill_excludes_student_state(self) -> None:
        block = JS.split("function configureReportLink", 1)[1].split(
            "function showRetryFeedback", 1
        )[0]
        self.assertIn("Question ID:", block)
        self.assertIn("Mode:", block)
        self.assertIn("Page:", block)
        self.assertIn("Suggested correction:", block)
        for forbidden in ("selectedAnswer", "score:", "progress:", "navigator"):
            self.assertNotIn(forbidden, block)


if __name__ == "__main__":
    unittest.main()
