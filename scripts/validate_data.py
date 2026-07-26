#!/usr/bin/env python3
"""Validate Sentence Sense Detective data, public content, and deployment invariants."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "questions.json"
PUBLIC_JSON = ROOT / "docs" / "data" / "questions.json"
DOCS = ROOT / "docs"

EXPECTED_MODE_COUNTS = {
    "parts-of-speech": 50,
    "sentence-elements": 44,
    "clauses": 62,
}
EXPECTED_REVIEWED = 106
EXPECTED_PROVISIONAL_POS = 50
EXPECTED_TOTAL = 156

PROHIBITED_PUBLIC_PATTERNS = {
    "annotation-system abbreviation": re.compile(r"\bUD\b", re.IGNORECASE),
    "parser package name": re.compile(r"\bStanza\b", re.IGNORECASE),
    "technical preparation term": re.compile(r"\bremap(?:ping|ped|s)?\b", re.IGNORECASE),
    "technical transformation term": re.compile(r"\bmapping\b", re.IGNORECASE),
    "parser internals": re.compile(r"\bparser\b", re.IGNORECASE),
    "technical review class": re.compile(r"\bmanual[- ]review\b", re.IGNORECASE),
    "technical rule class": re.compile(r"\brule[- ]based\b", re.IGNORECASE),
    "private evaluation term": re.compile(r"\bgold (?:label|analysis|answer|case)\b", re.IGNORECASE),
    "private preparation artifact": re.compile(
        r"\b(?:spreadsheet|validation row|source review|review note|regression test)\b",
        re.IGNORECASE,
    ),
    "draft product term": re.compile(r"\bscaffold\b", re.IGNORECASE),
    "private review status": re.compile(r"\b(?:teacher-reviewed|provisional)\b", re.IGNORECASE),
}


def nth_index(haystack: str, needle: str, occurrence: int) -> int:
    source = haystack.casefold()
    target = needle.casefold()
    start = 0
    found = -1
    for _ in range(occurrence + 1):
        found = source.find(target, start)
        if found < 0:
            return -1
        start = found + len(target)
    return found


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    payload = json.loads(CANONICAL.read_text(encoding="utf-8"))
    public = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])

    if len(questions) != EXPECTED_TOTAL:
        fail(errors, f"Expected {EXPECTED_TOTAL} canonical questions, found {len(questions)}")

    ids = [question.get("id") for question in questions]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        fail(errors, f"Duplicate question IDs: {duplicates}")

    mode_counts = Counter(question.get("mode") for question in questions)
    if dict(mode_counts) != EXPECTED_MODE_COUNTS:
        fail(errors, f"Unexpected mode counts: {dict(mode_counts)}")

    reviewed = [question for question in questions if question.get("status") == "teacher-reviewed"]
    provisional = [question for question in questions if question.get("status") == "provisional-scaffold"]
    if len(reviewed) != EXPECTED_REVIEWED:
        fail(errors, f"Expected {EXPECTED_REVIEWED} reviewed questions, found {len(reviewed)}")
    if len(provisional) != EXPECTED_PROVISIONAL_POS:
        fail(errors, f"Expected {EXPECTED_PROVISIONAL_POS} provisional POS questions, found {len(provisional)}")

    reviewed_source_ids = [question.get("source_id") for question in reviewed]
    if len(set(reviewed_source_ids)) != EXPECTED_REVIEWED:
        fail(errors, "Reviewed source IDs must be present exactly once")
    if any(question.get("mode") == "parts-of-speech" for question in reviewed):
        fail(errors, "Reviewed source questions must remain in Sentence Elements or Clauses")
    if any(question.get("mode") != "parts-of-speech" for question in provisional):
        fail(errors, "Provisional scaffold questions must remain in Parts of Speech")

    for question in questions:
        qid = question.get("id", "<missing>")
        required = {
            "id", "source_id", "language", "mode", "subskill", "sentence",
            "targets", "prompt", "answer", "options", "explanation", "status"
        }
        missing = sorted(required - set(question))
        if missing:
            fail(errors, f"{qid}: missing fields {missing}")
            continue
        if question["language"] != "en":
            fail(errors, f"{qid}: current pilot must use language=en")
        if len(question["options"]) != 4 or len(set(question["options"])) != 4:
            fail(errors, f"{qid}: options must contain exactly four unique values")
        if question["answer"] not in question["options"]:
            fail(errors, f"{qid}: answer is missing from options")
        if not question["targets"]:
            fail(errors, f"{qid}: at least one target is required")
        for target in question["targets"]:
            text = str(target.get("text", ""))
            occurrence = int(target.get("occurrence", 0))
            if not text or nth_index(question["sentence"], text, occurrence) < 0:
                fail(errors, f"{qid}: target {text!r} occurrence {occurrence} not found")
        if not str(question["prompt"]).strip() or not str(question["explanation"]).strip():
            fail(errors, f"{qid}: prompt and explanation must be non-empty")

    operator = next((q for q in questions if q.get("id") == "SE-P-02"), None)
    if not operator:
        fail(errors, "SE-P-02 is missing")
    else:
        if operator.get("answer") != "Operator":
            fail(errors, "SE-P-02 must use Operator as a separate answer category")
        if operator.get("targets") != [{"text": "Did", "occurrence": 0}]:
            fail(errors, "SE-P-02 must highlight Did only")

    if payload.get("metadata", {}).get("round_size") != 10:
        fail(errors, "Round size must remain 10")
    scoring = payload.get("metadata", {}).get("scoring", {})
    expected_scoring = {
        "first_attempt_correct": 1,
        "retry_correct": 0,
        "show_answer": 0,
        "negative_points": False,
    }
    if scoring != expected_scoring:
        fail(errors, f"Unexpected scoring configuration: {scoring}")

    public_questions = public.get("questions", [])
    if len(public_questions) != EXPECTED_TOTAL:
        fail(errors, "Public question count differs from canonical count")
    public_ids = [question.get("id") for question in public_questions]
    if public_ids != ids:
        fail(errors, "Public question order or IDs differ from canonical data")
    for question in public_questions:
        forbidden_fields = {"source_id", "status", "teacher_comment", "private_note"}
        leaked = sorted(forbidden_fields & set(question))
        if leaked:
            fail(errors, f"{question.get('id')}: public data leaks fields {leaked}")

    allowed_public_metadata = {
        "title", "language", "version", "round_size", "question_count", "scoring"
    }
    unexpected_metadata = sorted(set(public.get("metadata", {})) - allowed_public_metadata)
    if unexpected_metadata:
        fail(errors, f"Public metadata leaks internal fields {unexpected_metadata}")

    for path in DOCS.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".js", ".css", ".json", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PROHIBITED_PUBLIC_PATTERNS.items():
            match = pattern.search(text)
            if match:
                relative = path.relative_to(ROOT)
                fail(errors, f"{relative}: prohibited {label}: {match.group(0)!r}")

    if (DOCS / "teacher_notes.json").exists() or any("teacher_notes" in p.name for p in DOCS.rglob("*")):
        fail(errors, "Private teacher notes must not exist under docs/")

    if errors:
        print("Sentence Sense Detective validation failed:\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Sentence Sense Detective validation passed.")
    print(f"- Questions: {len(questions)}")
    print(f"- Reviewed source cases: {len(reviewed)}")
    print(f"- Provisional POS questions: {len(provisional)}")
    print(f"- Mode counts: {dict(mode_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
