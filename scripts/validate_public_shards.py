#!/usr/bin/env python3
"""Validate public shard integrity, field whitelists, and static-site budgets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "docs" / "data" / "en"
DOCS_ROOT = ROOT / "docs"
MANIFEST_LIMIT = 250 * 1024
SHARD_TARGET = 500 * 1024
SHARD_HARD_LIMIT = 1024 * 1024
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
}
TECHNICAL_EXERCISE_PATTERNS = {
    "Stanza": re.compile(r"\bStanza\b", re.IGNORECASE),
    "Universal Dependencies": re.compile(r"\bUniversal Dependencies\b", re.IGNORECASE),
    "UD abbreviation": re.compile(r"\bUD\b"),
    "raw dependency relation": re.compile(
        r"\b(?:nsubj|csubj|iobj|obj|obl|ccomp|xcomp|advcl|advmod|nmod|acl|amod)\b"
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, default=PUBLIC_ROOT)
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = args.public_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Public shard validation failed: {error}", file=sys.stderr)
        return 1
    manifest_bytes = manifest_path.stat().st_size
    if manifest_bytes > MANIFEST_LIMIT:
        errors.append(f"manifest is {manifest_bytes} bytes; limit is {MANIFEST_LIMIT}")

    question_ids = set()
    sentence_text_by_id = {}
    mode_counts = Counter()
    review_counts = Counter()
    largest_shard = ("", 0)
    actual_paths = set()
    for shard in manifest.get("shards", []):
        relative = Path(shard.get("path", ""))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"unsafe shard path: {relative}")
            continue
        path = args.public_root / relative
        actual_paths.add(relative.as_posix())
        if not path.exists():
            errors.append(f"missing shard: {relative}")
            continue
        content = path.read_bytes()
        size = len(content)
        if size > largest_shard[1]:
            largest_shard = (relative.as_posix(), size)
        if size > SHARD_HARD_LIMIT:
            errors.append(f"{relative}: {size} bytes exceeds the 1 MB hard limit")
        elif size > SHARD_TARGET:
            warnings.append(f"{relative}: {size} bytes exceeds the 500 KB target")
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
        review_counts[shard.get("tier")] += len(questions)
        for question in questions:
            question_id = question.get("id", "<missing>")
            if set(question) != PUBLIC_FIELDS:
                errors.append(
                    f"{question_id}: public fields differ from whitelist: "
                    f"{sorted(set(question) ^ PUBLIC_FIELDS)}"
                )
            if question_id in question_ids:
                errors.append(f"duplicate public question ID: {question_id}")
            question_ids.add(question_id)
            if question.get("mode") != shard.get("mode"):
                errors.append(f"{question_id}: question mode differs from shard")
            mode_counts[question.get("mode")] += 1
            sentence_id = question.get("sentence_id")
            sentence_text = question.get("sentence")
            if sentence_id in sentence_text_by_id and sentence_text_by_id[sentence_id] != sentence_text:
                errors.append(f"{sentence_id}: inconsistent public sentence text")
            sentence_text_by_id[sentence_id] = sentence_text
            spans = question.get("target_spans")
            if not isinstance(spans, list) or not spans:
                errors.append(f"{question_id}: missing target spans")
            else:
                for span in spans:
                    start = span.get("start")
                    end = span.get("end")
                    if (
                        not isinstance(start, int)
                        or not isinstance(end, int)
                        or start < 0
                        or end <= start
                        or not isinstance(sentence_text, str)
                        or end > len(sentence_text)
                    ):
                        errors.append(f"{question_id}: invalid Unicode span {span!r}")
            options = question.get("options")
            if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4:
                errors.append(f"{question_id}: options are not four unique values")
            elif question.get("answer") not in options:
                errors.append(f"{question_id}: answer is absent from options")
            exercise_text = json.dumps(question, ensure_ascii=False)
            for label, pattern in TECHNICAL_EXERCISE_PATTERNS.items():
                if pattern.search(exercise_text):
                    errors.append(f"{question_id}: public exercise contains {label}")

    committed_paths = {
        path.relative_to(args.public_root).as_posix()
        for path in args.public_root.rglob("*.json")
        if path.name != "manifest.json"
    }
    if committed_paths != actual_paths:
        errors.append(
            "public JSON files differ from manifest: "
            f"{sorted(committed_paths ^ actual_paths)}"
        )

    totals = manifest.get("totals", {})
    expected_totals = {
        "sentences": len(sentence_text_by_id),
        "questions": len(question_ids),
        "teacher_reviewed": review_counts["reviewed-core"],
        "provisional": review_counts["provisional"],
        "by_mode": {
            mode["id"]: mode_counts[mode["id"]]
            for mode in manifest.get("modes", [])
        },
    }
    if totals != expected_totals:
        errors.append(f"manifest totals differ: expected {expected_totals}, found {totals}")

    docs_size = sum(path.stat().st_size for path in args.docs_root.rglob("*") if path.is_file())
    if docs_size > DOCS_LIMIT:
        errors.append(f"docs/ is {docs_size} bytes; limit is {DOCS_LIMIT}")

    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if errors:
        print("Public shard validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Public shard validation passed.")
    print(f"- Manifest: {manifest_bytes} bytes")
    print(f"- Shards: {len(manifest.get('shards', []))}")
    print(f"- Largest shard: {largest_shard[0]} ({largest_shard[1]} bytes)")
    print(f"- Site size: {docs_size} bytes")
    print(f"- Sentences: {len(sentence_text_by_id)}")
    print(f"- Questions: {len(question_ids)}")
    print(f"- Reviewed: {review_counts['reviewed-core']}")
    print(f"- Provisional: {review_counts['provisional']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
