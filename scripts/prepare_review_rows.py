#!/usr/bin/env python3
"""Prepare formal-remap rows for the full and stratified review workbooks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pipeline_common import ROOT, SEED, read_jsonl, write_json

DEFAULT_INPUT = (
    ROOT / "data" / "generated" / "question_candidates.jsonl.gz"
)
DEFAULT_ROWS = ROOT / "external" / "review" / "review_pack_rows.json"
DEFAULT_SAMPLE = ROOT / "external" / "review" / "remap_manual_review_sample_rows.json"

HEADERS = [
    "question ID",
    "remap candidate ID",
    "sentence ID",
    "genre",
    "source corpus",
    "difficulty",
    "sentence",
    "highlighted target",
    "mode",
    "subskill",
    "dimension",
    "proposed answer",
    "four options",
    "explanation",
    "confidence",
    "remap profile",
    "profile SHA-256",
    "formal rule ID",
    "decision class",
    "formal action",
    "source case IDs",
    "matched Stanza evidence",
    "Stanza version",
    "model bundle SHA-256",
    "review status",
    "review reason",
    "review category",
    "accept / correct / reject",
    "corrected target",
    "corrected answer",
    "corrected explanation",
    "reviewer",
    "review date",
    "note",
]


def target_text(question: dict) -> str:
    return " … ".join(
        question["sentence"][span["start"]:span["end"]]
        for span in question["target_spans"]
    )


def review_category(question: dict) -> str:
    if question["review_status"] != "needs-review":
        return "publishable"
    reason = str(question.get("review_reason") or "")
    if reason.startswith("Incompatible formal rules"):
        return "conflict"
    if "parser mismatch" in reason.casefold():
        return "parser mismatch"
    return "manual guard"


def review_row(question: dict) -> list:
    return [
        question["question_id"],
        question["remap_candidate_id"],
        question["sentence_id"],
        question["genre"],
        question["source_corpus"],
        question["difficulty"],
        question["sentence"],
        target_text(question),
        question["mode"],
        question["subskill"],
        question["dimension"],
        question["answer"],
        "\n".join(question["options"]),
        question["explanation"],
        float(question["confidence"]),
        question["remap_profile"],
        question["remap_profile_sha256"],
        question["rule_id"],
        question["decision_class"],
        question["action"],
        "\n".join(question["source_case_ids"]),
        json.dumps(
            question["matched_evidence"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        question["stanza_version"],
        question["model_bundle_sha256"],
        question["review_status"],
        question.get("review_reason") or "",
        review_category(question),
        "",
        "",
        "",
        "",
        "",
        None,
        question.get("review_reason") or "",
    ]


def sample_key(question: dict) -> str:
    return hashlib.sha256(
        f"{SEED}\0review-sample\0{question['question_id']}".encode("utf-8")
    ).hexdigest()


def stratified_review_sample(
    questions: list[dict],
    sample_size: int,
) -> list[dict]:
    review_only = [
        question
        for question in questions
        if question["review_status"] == "needs-review"
    ]
    strata: dict[tuple, list[dict]] = {}
    for question in review_only:
        key = (
            question["rule_id"],
            question["answer"],
            question["review_reason"],
            question["genre"],
            question["difficulty"],
            question["source_corpus"],
        )
        strata.setdefault(key, []).append(question)
    for items in strata.values():
        items.sort(key=sample_key)
    keys = sorted(
        strata,
        key=lambda key: hashlib.sha256(
            f"{SEED}\0review-stratum\0{key}".encode("utf-8")
        ).hexdigest(),
    )
    selected = []
    selected_ids = set()
    for category in ("manual guard", "conflict", "parser mismatch"):
        category_items = sorted(
            (
                question
                for question in review_only
                if review_category(question) == category
            ),
            key=sample_key,
        )
        if category_items:
            selected.append(category_items[0])
            selected_ids.add(category_items[0]["question_id"])
    depth = 0
    while len(selected) < sample_size:
        added = False
        for key in keys:
            if depth < len(strata[key]):
                candidate = strata[key][depth]
                if candidate["question_id"] in selected_ids:
                    continue
                selected.append(candidate)
                selected_ids.add(candidate["question_id"])
                added = True
                if len(selected) == sample_size:
                    break
        if not added:
            break
        depth += 1
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--sample-size", type=int, default=100)
    args = parser.parse_args()
    try:
        questions = list(read_jsonl(args.input))
        if not questions:
            raise ValueError("question candidate input is empty")
        payload = {
            "headers": HEADERS,
            "rows": [review_row(question) for question in questions],
            "metadata": {
                "seed": SEED,
                "candidate_count": len(questions),
                "purpose": "full generated-candidate review pack",
            },
        }
        sample_questions = stratified_review_sample(
            questions,
            args.sample_size,
        )
        sample = {
            "headers": HEADERS,
            "rows": [review_row(question) for question in sample_questions],
            "metadata": {
                "seed": SEED,
                "sample_count": len(sample_questions),
                "candidate_count": len(questions),
                "profile_id": sample_questions[0]["remap_profile"],
                "profile_sha256": sample_questions[0][
                    "remap_profile_sha256"
                ],
                "candidate_review_category_counts": {
                    category: sum(
                        review_category(question) == category
                        for question in questions
                    )
                    for category in (
                        "manual guard",
                        "conflict",
                        "parser mismatch",
                        "publishable",
                    )
                },
                "review_only": True,
                "review_category_counts": {
                    category: sum(
                        review_category(question) == category
                        for question in sample_questions
                    )
                    for category in (
                        "manual guard",
                        "conflict",
                        "parser mismatch",
                    )
                },
                "stratification": [
                    "formal rule",
                    "answer",
                    "review reason",
                    "genre",
                    "difficulty",
                    "source corpus",
                ],
                "purpose": (
                    "deterministic stratified formal-remap manual-review sample"
                ),
            },
        }
        write_json(args.rows, payload)
        write_json(args.sample, sample)
        print(
            f"Prepared {len(questions)} review rows and a "
            f"{len(sample_questions)}-question sample."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Review-row preparation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
