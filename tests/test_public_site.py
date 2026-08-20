from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_data import (  # noqa: E402
    TECHNICAL_EXPLANATION_PATHS,
    validate_public_terms,
)

HTML = (ROOT / "docs/index.html").read_text(encoding="utf-8")
HANDBOOK = (ROOT / "docs/handbook.html").read_text(encoding="utf-8")
JS = (ROOT / "docs/assets/app.js").read_text(encoding="utf-8")
ROUND_STATE = (ROOT / "docs/assets/round-state.js").read_text(encoding="utf-8")
QUESTION_BANK = (ROOT / "docs/assets/question-bank.js").read_text(encoding="utf-8")
CSS = (ROOT / "docs/assets/styles.css").read_text(encoding="utf-8")
REMAP_CSS = (ROOT / "docs/assets/remapping.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "docs/data/manifest.json").read_text(encoding="utf-8"))


class PublicSiteTests(unittest.TestCase):
    def test_product_name_modes_and_counts(self) -> None:
        self.assertIn("Sentence Sense Detective", HTML)
        self.assertEqual(
            ["Parts of Speech", "Sentence Elements", "Clauses"],
            [mode["title"] for mode in MANIFEST["modes"]],
        )
        self.assertEqual(10_000, MANIFEST["totals"]["corpus_sentences"])
        self.assertEqual(106, MANIFEST["totals"]["reviewed_questions"])
        self.assertGreaterEqual(MANIFEST["totals"]["questions"], 10_156)
        self.assertGreaterEqual(MANIFEST["totals"]["sentences"], 10_000)

    def test_manifest_is_initial_payload_and_shards_are_lazy(self) -> None:
        self.assertNotIn("data/questions.js", HTML)
        self.assertNotIn("SENTENCE_SENSE_DATA", JS)
        self.assertIn("data/manifest.json", JS)
        self.assertIn("async function fetchShard", JS)
        self.assertIn("async function fetchGold", JS)
        self.assertIn("MAX_CACHED_SHARDS = 2", JS)
        self.assertIn("loadModeRound(button.dataset.mode)", JS)

    def test_public_shards_match_manifest_and_strip_internal_fields(self) -> None:
        public_fields = {
            "id", "sentence_id", "language", "mode", "subskill", "sentence",
            "target_spans", "prompt", "answer", "options", "explanation",
            "difficulty", "dimension",
        }
        seen = set()
        gold_path = ROOT / "docs/data" / MANIFEST["gold"]["path"]
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        self.assertEqual(106, len(gold["questions"]))
        for question in gold["questions"]:
            self.assertEqual(public_fields, set(question))
            seen.add(question["id"])
        for shard in MANIFEST["shards"]:
            path = ROOT / "docs/data" / shard["path"]
            content = path.read_bytes()
            self.assertEqual(shard["bytes"], len(content))
            self.assertEqual(shard["sha256"], hashlib.sha256(content).hexdigest())
            payload = json.loads(content)
            self.assertEqual(shard["count"], len(payload["questions"]))
            for question in payload["questions"]:
                self.assertEqual(public_fields, set(question))
                self.assertNotIn(question["id"], seen)
                seen.add(question["id"])
        self.assertEqual(MANIFEST["totals"]["questions"], len(seen))

    def test_brand_and_favicon_assets(self) -> None:
        assets = (
            "logo-mark.svg", "favicon.svg", "favicon-16x16.png",
            "favicon-32x32.png", "apple-touch-icon.png", "icon-192.png",
            "icon-512.png",
        )
        for asset in assets:
            self.assertTrue((ROOT / "docs/assets/brand" / asset).is_file(), asset)
        self.assertTrue((ROOT / "docs/assets/brand/site.webmanifest").is_file())
        self.assertIn('src="assets/brand/logo-mark.svg"', HTML)
        self.assertNotIn("🔎", HTML)

    def test_about_methodology_is_exact_and_version_is_dynamic(self) -> None:
        self.assertEqual(1, HTML.count("<!-- PUBLIC_METHODOLOGY_ALLOWLIST_START -->"))
        self.assertEqual(1, HTML.count("<!-- PUBLIC_METHODOLOGY_ALLOWLIST_END -->"))
        self.assertIn("The defining methodological feature of Sentence Sense Detective is a formal remapping layer", HTML)
        self.assertIn("The current engine reproduces all 106 reviewed cases exactly", HTML)
        self.assertIn("The current English release is built on 10,000 openly reusable corpus sentences", HTML)
        self.assertIn("Martin Grad — Principal author and grammar lead", HTML)
        self.assertIn("Damjan Popič — Co-author and project lead", HTML)
        self.assertIn('href="credits.html"', HTML)
        self.assertIn('id="about-version"', HTML)
        self.assertIn("els.aboutVersion.textContent = loaded.version", JS)
        self.assertEqual([], validate_public_terms(HTML))

    def test_remapping_is_prominent_and_placeholders_are_neutral(self) -> None:
        self.assertIn('class="remap-feature"', HTML)
        self.assertIn('href="handbook.html#remapping"', HTML)
        self.assertIn("Formal remapping turns corpus annotation into classroom grammar.", HTML)
        self.assertIn('id="remapping"', HANDBOOK)
        self.assertIn("Remapping is the central methodological contribution", HANDBOOK)
        self.assertIn("Content in preparation", HANDBOOK)
        self.assertIn("Expanded content coming.", HANDBOOK)
        self.assertIn(".remap-feature", REMAP_CSS)
        combined = HTML + HANDBOOK
        for forbidden in (
            "To be expanded by Martin Grad",
            "To be amended by Martin Grad",
            "[MARTIN:",
        ):
            self.assertNotIn(forbidden, combined)

    def test_technical_methodology_stays_out_of_exercise_code(self) -> None:
        self.assertEqual(
            {
                Path("docs/index.html"),
                Path("docs/handbook.html"),
                Path("docs/assets/remapping.css"),
            },
            TECHNICAL_EXPLANATION_PATHS,
        )
        for public_exercise_code in (JS, ROUND_STATE, QUESTION_BANK):
            self.assertNotIn("Stanza", public_exercise_code)
            self.assertNotIn("Universal Dependencies", public_exercise_code)
            self.assertNotIn("formal remapping", public_exercise_code.casefold())

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
        self.assertIn("recent_question_ids_per_mode", JS)
        self.assertIn("recent_sentence_ids_per_mode", JS)
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

    def test_report_link_contains_the_required_question_context(self) -> None:
        block = JS.split("function configureReportLink", 1)[1].split(
            "function showRetryFeedback", 1
        )[0]
        self.assertIn("Question ID:", block)
        self.assertIn("Mode:", block)
        self.assertIn("Sentence:", block)
        self.assertIn("Highlighted target:", block)
        self.assertIn("Displayed answer:", block)
        self.assertIn("App version:", block)
        self.assertIn("Report:", block)
        for forbidden in ("selectedAnswer", "score:", "progress:", "navigator"):
            self.assertNotIn(forbidden, block)

    def test_mobile_about_contract(self) -> None:
        self.assertIn("max-height: min(86vh, 760px)", CSS)
        self.assertIn("@media (max-width: 360px)", CSS)
        self.assertIn(".author-cards { grid-template-columns: 1fr; }", CSS)


if __name__ == "__main__":
    unittest.main()
