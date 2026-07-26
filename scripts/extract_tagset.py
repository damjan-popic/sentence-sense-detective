#!/usr/bin/env python3
"""Materialise the locked English public answer inventory from the 156 pilot items."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pipeline_common import ROOT, read_jsonl, write_json

OUTPUT = ROOT / "config" / "pedagogical_tagset_en.json"
QUESTION_ROOT = ROOT / "data" / "questions" / "en"

DIMENSION_BY_MODE_SUBSKILL = {
    ("parts-of-speech", "Parts of speech"): "word_class",
    ("sentence-elements", "Sentence elements"): "sentence_element",
    ("clauses", "Clause type"): "clause_type",
    ("clauses", "Clause marker"): "clause_marker",
    ("clauses", "Clause structure"): "clause_structure",
    ("clauses", "Clause function"): "clause_function",
}


def build() -> dict:
    questions = list(read_jsonl(QUESTION_ROOT / "reviewed-core.jsonl"))
    for path in sorted(QUESTION_ROOT.glob("provisional-*.jsonl")):
        questions.extend(read_jsonl(path))
    dimensions = defaultdict(
        lambda: {
            "mode": None,
            "subskill": None,
            "prompts": set(),
            "labels": set(),
        }
    )
    for question in questions:
        key = (question["mode"], question["subskill"])
        dimension = DIMENSION_BY_MODE_SUBSKILL[key]
        entry = dimensions[dimension]
        entry["mode"] = question["mode"]
        entry["subskill"] = question["subskill"]
        entry["prompts"].add(question["prompt"])
        entry["labels"].update(question["options"])
        entry["labels"].add(question["answer"])
    return {
        "version": "1.0.0",
        "language": "en",
        "source_question_count": len(questions),
        "locked_reviewed_question_count": sum(
            question["review_status"] == "teacher-reviewed"
            for question in questions
        ),
        "operator_is_separate": True,
        "dimensions": {
            name: {
                "mode": value["mode"],
                "subskill": value["subskill"],
                "prompts": sorted(value["prompts"]),
                "labels": sorted(value["labels"]),
            }
            for name, value in sorted(dimensions.items())
        },
    }


if __name__ == "__main__":
    payload = build()
    write_json(OUTPUT, payload)
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)} with "
        f"{sum(len(item['labels']) for item in payload['dimensions'].values())} labels."
    )
