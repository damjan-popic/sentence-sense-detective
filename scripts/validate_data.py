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
METHODOLOGY_PARAGRAPH = (
    "<p>The English pilot began with 106 examples reviewed by an experienced grammar "
    "teacher. Behind the scenes, we are testing how sentences annotated automatically "
    "with Stanza and Universal Dependencies can be translated into the grammatical "
    "categories students actually use in class. Students do not need to learn UD labels: "
    "that technical layer belongs to corpus preparation, not to the learning task. The "
    "reviewed examples remain our reference set; larger automatically prepared batches "
    "are provisional until they are checked and corrected.</p>"
)
RAW_RELATIONS = re.compile(
    r"\b(?:nsubj|csubj|iobj|obj|obl|ccomp|xcomp|advcl|advmod|nmod|acl|amod)\b"
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
    start_marker = "<!-- methodology-note:start -->"
    end_marker = "<!-- methodology-note:end -->"
    if index_html.count(start_marker) != 1 or index_html.count(end_marker) != 1:
        errors.append("the About methodology whitelist markers must each occur once")
        allowed_block = ""
    else:
        allowed_block = index_html.split(start_marker, 1)[1].split(end_marker, 1)[0].strip()
        if allowed_block != METHODOLOGY_PARAGRAPH:
            errors.append("the About methodology paragraph differs from the authoritative brief")

    required_assets = (
        "assets/logo-mark.svg",
        "assets/favicon.svg",
        "assets/favicon-16x16.png",
        "assets/favicon-32x32.png",
        "assets/apple-touch-icon.png",
        "assets/icon-192.png",
        "assets/icon-512.png",
        "site.webmanifest",
    )
    for relative in required_assets:
        if not (DOCS / relative).exists():
            errors.append(f"missing supplied brand asset: docs/{relative}")
    for reference in (
        'src="assets/logo-mark.svg"',
        'href="assets/favicon.svg"',
        'href="assets/favicon-16x16.png"',
        'href="assets/favicon-32x32.png"',
        'href="assets/apple-touch-icon.png"',
        'href="site.webmanifest"',
    ):
        if reference not in index_html:
            errors.append(f"index.html does not reference {reference}")
    if "🔎" in index_html:
        errors.append("the old emoji brand mark is still present")
    if 'src="data/questions.js"' in index_html:
        errors.append("the monolithic browser question payload is still referenced")
    if (DOCS / "data" / "questions.js").exists() or (DOCS / "data" / "questions.json").exists():
        errors.append("legacy monolithic public question files still exist")

    public_text_files = {
        ".html", ".js", ".css", ".json", ".webmanifest", ".txt", ".svg"
    }
    for path in DOCS.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in public_text_files:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path == index_path and allowed_block:
            text = text.replace(
                f"{start_marker}\n      {allowed_block}\n      {end_marker}",
                "",
                1,
            )
        for label, pattern in (
            ("Stanza", re.compile(r"\bStanza\b", re.IGNORECASE)),
            ("Universal Dependencies", re.compile(r"\bUniversal Dependencies\b", re.IGNORECASE)),
            ("UD abbreviation", re.compile(r"\bUD\b")),
            ("raw dependency relation", RAW_RELATIONS),
        ):
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: {label} appears outside the whitelist")
                break

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
