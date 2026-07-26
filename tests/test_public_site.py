from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")
ROUND_STATE = (ROOT / "docs" / "assets" / "round-state.js").read_text(encoding="utf-8")
CSS = (ROOT / "docs" / "assets" / "styles.css").read_text(encoding="utf-8")
PUBLIC = json.loads((ROOT / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))


class PublicSiteTests(unittest.TestCase):
    def test_product_name_and_modes(self) -> None:
        self.assertIn("Sentence Sense Detective", HTML)
        titles = [mode["title"] for mode in PUBLIC["modes"]]
        self.assertEqual(["Parts of Speech", "Sentence Elements", "Clauses"], titles)

    def test_required_interactions_exist(self) -> None:
        for element_id in (
            "show-answer", "next-question", "review-mistakes", "score-value",
            "streak-value", "breakdown-list", "mistakes-list"
        ):
            self.assertIn(f'id="{element_id}"', HTML)
        self.assertIn("one more try", JS)
        self.assertIn("firstTryCorrect", JS)
        self.assertIn("localStorage", JS)
        self.assertIn("SentenceSenseRound", JS)
        self.assertIn('src="assets/round-state.js"', HTML)
        self.assertIn("retry-available", ROUND_STATE)

    def test_public_payload_strips_maintenance_fields(self) -> None:
        for question in PUBLIC["questions"]:
            self.assertNotIn("source_id", question)
            self.assertNotIn("status", question)
            self.assertNotIn("teacher_comment", question)
        self.assertEqual(
            {
                "title", "language", "version",
                "round_size", "question_count", "scoring",
            },
            set(PUBLIC["metadata"]),
        )

    def test_public_copy_has_no_draft_language(self) -> None:
        self.assertNotIn("scaffold", HTML.casefold())

    def test_accessibility_contracts_are_present(self) -> None:
        self.assertIn('<main id="main" tabindex="-1">', HTML)
        self.assertIn('role="progressbar"', HTML)
        self.assertIn('aria-live="polite"', HTML)
        self.assertIn('id="question-card" class="question-card" tabindex="-1"', HTML)
        self.assertIn('id="summary-title" tabindex="-1"', HTML)
        self.assertIn("focusWithoutScroll(els.questionCard)", JS)
        self.assertIn("focusWithoutScroll(els.summaryTitle)", JS)

    def test_reduced_motion_is_honoured_in_css_and_javascript(self) -> None:
        self.assertIn("@media (prefers-reduced-motion: reduce)", CSS)
        self.assertIn("return prefersReducedMotion() ? 'auto' : 'smooth';", JS)
        self.assertIn("if (prefersReducedMotion()) return;", JS)


if __name__ == "__main__":
    unittest.main()
