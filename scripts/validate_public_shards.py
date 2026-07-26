#!/usr/bin/env python3
"""Validate public gold/shard integrity, field boundaries, and static budgets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "docs" / "data"
DOCS_ROOT = ROOT / "docs"
MANIFEST_LIMIT = 250_000
SHARD_LIMIT = 500_000
INITIAL_TRANSFER_LIMIT = 500_000
DOCS_LIMIT = 250 * 1024 * 1024
PUBLIC_FIELDS = {
    "id",
    "sentence_id",
    "language",
    "mode",
    "subskill",
    "sentence",
    "target_spans",
    "prompt",
    "answer",
    "options",
    "explanation",
    "difficulty",
}
TECHNICAL_EXERCISE_PATTERNS = {
    "Stanza": re.compile(r"\bStanza\b", re.IGNORECASE),
    "Universal Dependencies": re.compile(r"\bUniversal Dependencies\b", re.IGNORECASE),
    "UD abbreviation": re.compile(r"\bUD\b"),
    "internal status": re.compile(
        r"\b(?:martin-reviewed|auto-high-confidence|human-reviewed|needs-review|rejected)\b",
        re.IGNORECASE,
    ),
    "development terminology": re.compile(
        r"\b(?:(?:re)?mapping|parser|provisional|rule-based|manual review)\b",
        re.IGNORECASE,
    ),
    "raw dependency relation": re.compile(
        r"\b(?:nsubj|csubj|iobj|obj|obl|ccomp|xcomp|advcl|advmod|nmod|acl|amod)\b"
    ),
}


def safe_public_path(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe public data path: {relative}")
    return root / relative


def validate_question(
    question: dict,
    *,
    expected_mode: str | None,
    question_ids: set[str],
    sentence_text_by_id: dict[str, str],
    errors: list[str],
) -> None:
    question_id = question.get("id", "<missing>")
    if set(question) != PUBLIC_FIELDS:
        errors.append(
            f"{question_id}: public fields differ from whitelist: "
            f"{sorted(set(question) ^ PUBLIC_FIELDS)}"
        )
    if question_id in question_ids:
        errors.append(f"duplicate public question ID: {question_id}")
    question_ids.add(question_id)
    if expected_mode and question.get("mode") != expected_mode:
        errors.append(f"{question_id}: question mode differs from its shard")
    if question.get("difficulty") not in {"basic", "intermediate", "advanced"}:
        errors.append(f"{question_id}: invalid or missing difficulty")
    sentence_id = question.get("sentence_id")
    sentence_text = question.get("sentence")
    if (
        sentence_id in sentence_text_by_id
        and sentence_text_by_id[sentence_id] != sentence_text
    ):
        errors.append(f"{sentence_id}: inconsistent public sentence text")
    sentence_text_by_id[sentence_id] = sentence_text
    spans = question.get("target_spans")
    if not isinstance(spans, list) or not spans:
        errors.append(f"{question_id}: missing target spans")
    else:
        previous_end = -1
        for span in sorted(spans, key=lambda value: value.get("start", -1)):
            start, end = span.get("start"), span.get("end")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start < 0
                or end <= start
                or not isinstance(sentence_text, str)
                or end > len(sentence_text)
                or start < previous_end
            ):
                errors.append(f"{question_id}: invalid Unicode span {span!r}")
            previous_end = end if isinstance(end, int) else previous_end
    options = question.get("options")
    if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4:
        errors.append(f"{question_id}: options are not four unique values")
    elif question.get("answer") not in options:
        errors.append(f"{question_id}: answer is absent from options")
    exercise_text = json.dumps(question, ensure_ascii=False)
    for label, pattern in TECHNICAL_EXERCISE_PATTERNS.items():
        if pattern.search(exercise_text):
            errors.append(f"{question_id}: public exercise contains {label}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, default=PUBLIC_ROOT)
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    args = parser.parse_args()
    errors = []
    manifest_path = args.public_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Public data validation failed: {error}", file=sys.stderr)
        return 1
    manifest_bytes = manifest_path.stat().st_size
    if manifest_bytes > MANIFEST_LIMIT:
        errors.append(f"manifest is {manifest_bytes} bytes; limit is {MANIFEST_LIMIT}")

    question_ids = set()
    gold_ids = set()
    sentence_text_by_id = {}
    mode_counts = Counter()
    subskill_counts = Counter()
    difficulty_counts = Counter()
    expected_paths = {"manifest.json"}

    gold_descriptor = manifest.get("gold", {})
    try:
        gold_path = safe_public_path(args.public_root, gold_descriptor.get("path", ""))
        expected_paths.add(gold_path.relative_to(args.public_root).as_posix())
        gold_content = gold_path.read_bytes()
        if gold_descriptor.get("bytes") != len(gold_content):
            errors.append("gold.json byte count differs from manifest")
        if gold_descriptor.get("sha256") != hashlib.sha256(gold_content).hexdigest():
            errors.append("gold.json SHA-256 differs from manifest")
        gold_payload = json.loads(gold_content)
        gold_questions = gold_payload.get("questions", [])
        if len(gold_questions) != 106 or gold_descriptor.get("count") != 106:
            errors.append("gold.json must contain exactly 106 questions")
        for question in gold_questions:
            validate_question(
                question,
                expected_mode=None,
                question_ids=question_ids,
                sentence_text_by_id=sentence_text_by_id,
                errors=errors,
            )
            gold_ids.add(question.get("id"))
            mode_counts[question.get("mode")] += 1
            subskill_counts[question.get("subskill")] += 1
            difficulty_counts[question.get("difficulty")] += 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"gold file validation failed: {error}")

    largest_shard = ("", 0)
    for shard in manifest.get("shards", []):
        try:
            path = safe_public_path(args.public_root, shard.get("path", ""))
        except ValueError as error:
            errors.append(str(error))
            continue
        relative = path.relative_to(args.public_root).as_posix()
        expected_paths.add(relative)
        if not path.exists():
            errors.append(f"missing shard: {relative}")
            continue
        content = path.read_bytes()
        size = len(content)
        if size > largest_shard[1]:
            largest_shard = (relative, size)
        if size > SHARD_LIMIT:
            errors.append(f"{relative}: {size} bytes exceeds the 500 KB limit")
        if shard.get("bytes") != size:
            errors.append(f"{relative}: byte count differs from manifest")
        if shard.get("sha256") != hashlib.sha256(content).hexdigest():
            errors.append(f"{relative}: SHA-256 differs from manifest")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            errors.append(f"{relative}: invalid JSON: {error}")
            continue
        questions = payload.get("questions")
        if payload.get("mode") != shard.get("mode"):
            errors.append(f"{relative}: payload mode differs from manifest")
        if not isinstance(questions, list) or shard.get("count") != len(questions):
            errors.append(f"{relative}: question count differs from manifest")
            continue
        actual_difficulty = Counter(
            question.get("difficulty") for question in questions
        )
        if shard.get("difficulty") != dict(sorted(actual_difficulty.items())):
            errors.append(f"{relative}: difficulty coverage differs from manifest")
        for question in questions:
            validate_question(
                question,
                expected_mode=shard.get("mode"),
                question_ids=question_ids,
                sentence_text_by_id=sentence_text_by_id,
                errors=errors,
            )
            mode_counts[question.get("mode")] += 1
            subskill_counts[question.get("subskill")] += 1
            difficulty_counts[question.get("difficulty")] += 1

    committed_paths = {
        path.relative_to(args.public_root).as_posix()
        for path in args.public_root.rglob("*.json")
    }
    if committed_paths != expected_paths:
        errors.append(
            "public JSON files differ from manifest: "
            f"{sorted(committed_paths ^ expected_paths)}"
        )

    totals = manifest.get("totals", {})
    if totals.get("questions") != len(question_ids):
        errors.append("manifest total question count differs from public files")
    if totals.get("sentences") != len(sentence_text_by_id):
        errors.append("manifest total sentence count differs from public files")
    if totals.get("corpus_sentences") != 10_000:
        errors.append("manifest must report exactly 10,000 corpus sentences")
    if totals.get("reviewed_questions") != len(gold_ids):
        errors.append("manifest reviewed count differs from gold.json")
    expected_by_mode = {
        mode["id"]: mode_counts[mode["id"]] for mode in manifest.get("modes", [])
    }
    if totals.get("by_mode") != expected_by_mode:
        errors.append("manifest mode counts differ from public files")
    if totals.get("by_subskill") != dict(sorted(subskill_counts.items())):
        errors.append("manifest subskill counts differ from public files")
    if totals.get("by_difficulty") != dict(sorted(difficulty_counts.items())):
        errors.append("manifest difficulty counts differ from public files")
    if sum(totals.get("by_source_corpus", {}).values()) != len(question_ids):
        errors.append("manifest source-corpus counts do not sum to total questions")

    policy = manifest.get("sampling_policy", {})
    if policy.get("recent_question_ids_per_mode", 0) > 250:
        errors.append("question history limit exceeds 250")
    if policy.get("recent_sentence_ids_per_mode", 0) > 150:
        errors.append("sentence history limit exceeds 150")

    initial_files = [
        args.docs_root / "index.html",
        args.docs_root / "assets" / "styles.css",
        args.docs_root / "assets" / "round-state.js",
        args.docs_root / "assets" / "question-bank.js",
        args.docs_root / "assets" / "app.js",
        manifest_path,
    ]
    initial_bytes = sum(path.stat().st_size for path in initial_files)
    if initial_bytes > INITIAL_TRANSFER_LIMIT:
        errors.append(
            f"initial transfer is {initial_bytes} bytes; limit is {INITIAL_TRANSFER_LIMIT}"
        )
    docs_size = sum(
        path.stat().st_size for path in args.docs_root.rglob("*") if path.is_file()
    )
    if docs_size > DOCS_LIMIT:
        errors.append(f"docs/ is {docs_size} bytes; limit is {DOCS_LIMIT}")

    if errors:
        print("Public data validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Public data validation passed.")
    print(f"- Manifest: {manifest_bytes} bytes")
    print(f"- Gold questions: {len(gold_ids)}")
    print(f"- Shards: {len(manifest.get('shards', []))}")
    print(f"- Largest shard: {largest_shard[0]} ({largest_shard[1]} bytes)")
    print(f"- Initial transfer: {initial_bytes} bytes")
    print(f"- Site size: {docs_size} bytes")
    print(f"- Sentences: {len(sentence_text_by_id)}")
    print(f"- Questions: {len(question_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
