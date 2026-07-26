#!/usr/bin/env python3
"""Validate the locked English pilot and public-facing content boundaries."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from corpus_io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXPECTED_MODE_COUNTS = {
    "parts-of-speech": 50,
    "sentence-elements": 44,
    "clauses": 62,
}
EXPECTED_REVIEWED = 106
EXPECTED_PROVISIONAL = 50
EXPECTED_TOTAL = 156
EXPECTED_SENTENCES = 92
REVIEWED_CONTRACT_HASH = "a6a15b586f8542e9792194e8f745951ef19c6030abf1fe1c71cdc8f41ff5d9a8"
HIGHLIGHT_CONTRACT_HASH = "3688077b0bf6e345e98ef88e85afc734660a79cf893ff2a1c9ffbe09a92d3a39"
QUESTION_CONTRACT_HASH = "e8a660c6e98830cdd272ccf665e8783b2771788bd27fd11ab05e03052fdb35ca"
METHODOLOGY_SECTION = (
    '<section id="about-methodology">\n'
    "      <h3>How the question bank is built</h3>\n"
    "      <p>The English pilot began with 106 examples prepared and reviewed by Martin "
    "Grad. To expand the bank, we use openly licensed language corpora and automatic "
    "linguistic analysis with Stanza and Universal Dependencies to identify candidate "
    "words, sentence elements, and clauses. These candidates are converted into the "
    "grammatical terminology used in teaching, filtered, tested, and corrected over time. "
    "The technical annotation is part of corpus preparation only: it is not the terminology "
    "students are expected to learn.</p>\n"
    "    </section>"
)
ALLOWLIST_START = "<!-- PUBLIC_METHODOLOGY_ALLOWLIST_START -->"
ALLOWLIST_END = "<!-- PUBLIC_METHODOLOGY_ALLOWLIST_END -->"
RAW_RELATIONS = re.compile(
    r"\b(?:nsubj|csubj|iobj|obj|obl|ccomp|xcomp|advcl|advmod|nmod|acl|amod)\b"
)
PUBLIC_PROHIBITED_PATTERNS = (
    ("Stanza", re.compile(r"\bStanza\b", re.IGNORECASE)),
    ("Universal Dependencies", re.compile(r"\bUniversal Dependencies\b", re.IGNORECASE)),
    ("UD abbreviation", re.compile(r"\bUD\b")),
    ("mapping terminology", re.compile(r"\b(?:re)?mapping\b", re.IGNORECASE)),
    ("parser terminology", re.compile(r"\bparser\b", re.IGNORECASE)),
    ("provisional terminology", re.compile(r"\bprovisional\b", re.IGNORECASE)),
    ("manual review terminology", re.compile(r"\bmanual review\b", re.IGNORECASE)),
    ("rule-based terminology", re.compile(r"\brule-based\b", re.IGNORECASE)),
    (
        "internal review status",
        re.compile(
            r"\b(?:martin-reviewed|auto-high-confidence|human-reviewed|needs-review|rejected)\b",
            re.IGNORECASE,
        ),
    ),
    ("raw dependency relation", RAW_RELATIONS),
)


def compact_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def target_contract(sentence: str, spans: list[dict]) -> list[dict]:
    targets = []
    for span in spans:
        text = sentence[span["start"]:span["end"]]
        occurrence = sentence[:span["start"]].casefold().count(text.casefold())
        targets.append({"text": text, "occurrence": occurrence})
    return targets


def validate_public_terms(index_html: str) -> list[str]:
    """Validate the single exact methodology allowance and scan all other public text."""
    errors: list[str] = []
    if index_html.count(ALLOWLIST_START) != 1 or index_html.count(ALLOWLIST_END) != 1:
        errors.append("the About methodology allowlist markers must each occur once")
        stripped_index = index_html
    else:
        before, remainder = index_html.split(ALLOWLIST_START, 1)
        allowed_block, after = remainder.split(ALLOWLIST_END, 1)
        if allowed_block.strip() != METHODOLOGY_SECTION:
            errors.append("the About methodology section differs from the authoritative copy")
        stripped_index = before + after

    public_text_files = {
        ".html", ".js", ".css", ".json", ".webmanifest", ".txt", ".svg"
    }
    for path in DOCS.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in public_text_files:
            continue
        text = stripped_index if path == DOCS / "index.html" else path.read_text(
            encoding="utf-8", errors="replace"
        )
        if path != DOCS / "index.html" and (
            ALLOWLIST_START in text or ALLOWLIST_END in text
        ):
            errors.append(
                f"{path.relative_to(ROOT)}: methodology allowlist markers are only permitted in docs/index.html"
            )
        for label, pattern in PUBLIC_PROHIBITED_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: {label} appears outside the allowlist")
                break
    return errors


def main() -> int:
    errors: list[str] = []
    sentence_records = []
    for path in sorted((ROOT / "data" / "corpus" / "en").glob("sentences-*.jsonl")):
        sentence_records.extend(read_jsonl(path))
    sentence_by_id = {record["id"]: record for record in sentence_records}
    annotations = read_jsonl(
        ROOT / "data" / "annotations" / "en" / "pedagogical-annotations.jsonl"
    )
    annotation_by_id = {record["id"]: record for record in annotations}
    reviewed = read_jsonl(ROOT / "data" / "questions" / "en" / "reviewed-core.jsonl")
    provisional = []
    for path in sorted((ROOT / "data" / "questions" / "en").glob("provisional-*.jsonl")):
        provisional.extend(read_jsonl(path))
    questions = provisional + reviewed
    config = json.loads(
        (ROOT / "data" / "questions" / "en" / "config.json").read_text(encoding="utf-8")
    )

    if len(sentence_records) != EXPECTED_SENTENCES:
        errors.append(f"expected {EXPECTED_SENTENCES} unique sentences, found {len(sentence_records)}")
    if len(questions) != EXPECTED_TOTAL:
        errors.append(f"expected {EXPECTED_TOTAL} questions, found {len(questions)}")
    if len(reviewed) != EXPECTED_REVIEWED:
        errors.append(f"expected {EXPECTED_REVIEWED} reviewed questions, found {len(reviewed)}")
    if len(provisional) != EXPECTED_PROVISIONAL:
        errors.append(f"expected {EXPECTED_PROVISIONAL} provisional questions, found {len(provisional)}")
    mode_counts = Counter(question["mode"] for question in questions)
    if dict(mode_counts) != EXPECTED_MODE_COUNTS:
        errors.append(f"unexpected mode counts: {dict(mode_counts)}")
    if len({question["source_id"] for question in reviewed}) != EXPECTED_REVIEWED:
        errors.append("all 106 reviewed source IDs must remain represented exactly once")
    if any(question["mode"] == "parts-of-speech" for question in reviewed):
        errors.append("reviewed source questions must remain in Sentence Elements or Clauses")
    if any(question["mode"] != "parts-of-speech" for question in provisional):
        errors.append("the 50 provisional pilot questions must remain Parts of Speech")

    joined = []
    for question in questions:
        sentence = sentence_by_id[question["sentence_id"]]["text"]
        spans = annotation_by_id[question["annotation_id"]]["target_spans"]
        joined.append(
            {
                **question,
                "sentence": sentence,
                "targets": target_contract(sentence, spans),
            }
        )
    highlight_contract = [
        {"id": q["id"], "sentence": q["sentence"], "targets": q["targets"]}
        for q in joined
    ]
    full_contract = [
        {
            field: q[field]
            for field in (
                "id", "source_id", "mode", "subskill", "sentence",
                "targets", "prompt", "answer",
            )
        }
        for q in joined
    ]
    reviewed_contract = [
        {
            field: q[field]
            for field in (
                "id", "source_id", "mode", "subskill", "sentence",
                "targets", "prompt", "answer",
            )
        }
        for q in joined
        if q["review_status"] == "teacher-reviewed"
    ]
    if compact_hash(highlight_contract) != HIGHLIGHT_CONTRACT_HASH:
        errors.append("one or more of the 156 migrated highlights changed")
    if compact_hash(full_contract) != QUESTION_CONTRACT_HASH:
        errors.append("one or more pilot IDs, answers, prompts, or terminology choices changed")
    if compact_hash(reviewed_contract) != REVIEWED_CONTRACT_HASH:
        errors.append("the 106 reviewed mappings no longer match the locked contract")

    operator = next((question for question in joined if question["id"] == "SE-P-02"), None)
    if not operator or operator["answer"] != "Operator" or operator["targets"] != [
        {"text": "Did", "occurrence": 0}
    ]:
        errors.append("SE-P-02 must retain Operator and highlight Did only")
    review_guard = next((question for question in joined if question["id"] == "REVIEW-01"), None)
    if (
        not review_guard
        or review_guard["answer"] != "Context needed"
        or "More context is needed" not in review_guard["explanation"]
    ):
        errors.append("the manual-review guard in REVIEW-01 must remain visible")

    expected_scoring = {
        "first_attempt_correct": 1,
        "retry_correct": 0,
        "show_answer": 0,
        "negative_points": False,
    }
    if config.get("round_size") != 10 or config.get("scoring") != expected_scoring:
        errors.append("round size or scoring changed")

    index_path = DOCS / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    errors.extend(validate_public_terms(index_html))

    required_assets = (
        "assets/brand/logo-mark.svg",
        "assets/brand/favicon.svg",
        "assets/brand/favicon-16x16.png",
        "assets/brand/favicon-32x32.png",
        "assets/brand/apple-touch-icon.png",
        "assets/brand/icon-192.png",
        "assets/brand/icon-512.png",
        "assets/brand/site.webmanifest",
    )
    for relative in required_assets:
        if not (DOCS / relative).exists():
            errors.append(f"missing supplied brand asset: docs/{relative}")
    for reference in (
        'src="assets/brand/logo-mark.svg"',
        'href="assets/brand/favicon.svg"',
        'href="assets/brand/favicon-16x16.png"',
        'href="assets/brand/favicon-32x32.png"',
        'href="assets/brand/apple-touch-icon.png"',
        'href="assets/brand/site.webmanifest"',
    ):
        if reference not in index_html:
            errors.append(f"index.html does not reference {reference}")
    if "🔎" in index_html:
        errors.append("the old emoji brand mark is still present")
    if 'src="data/questions.js"' in index_html:
        errors.append("the monolithic browser question payload is still referenced")
    if (DOCS / "data" / "questions.js").exists() or (DOCS / "data" / "questions.json").exists():
        errors.append("legacy monolithic public question files still exist")

    app_js = (DOCS / "assets" / "app.js").read_text(encoding="utf-8")
    if "els.aboutVersion.textContent" not in app_js:
        errors.append("About version is not populated from public metadata")
    if "MANIFEST_URL" not in app_js or "fetchShard" not in app_js:
        errors.append("the manifest-and-shards loader is missing")
    if not (ROOT / ".github" / "ISSUE_TEMPLATE" / "content-correction.md").exists():
        errors.append("the content-correction issue template is missing")
    for path in ROOT.rglob("*"):
        if path.is_file() and "Zone.Identifier" in path.name:
            errors.append(f"Windows Zone.Identifier artefact remains: {path.relative_to(ROOT)}")

    if errors:
        print("Sentence Sense Detective validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Sentence Sense Detective pilot validation passed.")
    print(f"- Sentences: {len(sentence_records)}")
    print(f"- Questions: {len(questions)}")
    print(f"- Reviewed source cases: {len(reviewed)}")
    print(f"- Provisional questions: {len(provisional)}")
    print(f"- Mode counts: {dict(mode_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
