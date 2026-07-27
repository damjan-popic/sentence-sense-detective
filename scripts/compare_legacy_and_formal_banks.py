#!/usr/bin/env python3
"""Compare the quarantined heuristic bank with the formal remap bank."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pipeline_common import ROOT, read_jsonl, write_json

LEGACY_ROOT = ROOT / "data/generated/legacy_handcoded_a1ed4bd"
DEFAULT_LEGACY = LEGACY_ROOT / "accepted_questions.jsonl"
DEFAULT_NEW_ACCEPTED = ROOT / "data/generated/accepted_questions.jsonl.gz"
DEFAULT_NEW_CANDIDATES = ROOT / "data/generated/question_candidates.jsonl.gz"
DEFAULT_REPORT = ROOT / "reports/remap_old_vs_new.json"
DEFAULT_MARKDOWN = ROOT / "reports/remap_old_vs_new.md"


def target_key(item: dict) -> tuple:
    return (
        item["sentence_id"],
        item["dimension"],
        tuple(
            (span["start"], span["end"])
            for span in item.get("target_spans", [])
        ),
    )


def family_key(item: dict) -> tuple[str, str]:
    return item["sentence_id"], item["dimension"]


def example(item: dict, category: str, **extra: object) -> dict:
    return {
        "category": category,
        "sentence_id": item["sentence_id"],
        "dimension": item["dimension"],
        "sentence": item["sentence"],
        "target_spans": item["target_spans"],
        "old_answer": item.get("answer"),
        "old_rule_id": item.get("rule_id"),
        **extra,
    }


def compare(
    legacy: list[dict],
    new_accepted: list[dict],
    new_candidates: list[dict],
) -> dict:
    new_exact = defaultdict(list)
    new_family = defaultdict(list)
    for item in new_accepted:
        new_exact[target_key(item)].append(item)
        new_family[family_key(item)].append(item)
    new_review_exact = defaultdict(list)
    new_review_family = defaultdict(list)
    for item in new_candidates:
        if item["review_status"] != "needs-review":
            continue
        new_review_exact[target_key(item)].append(item)
        new_review_family[family_key(item)].append(item)

    categories = Counter()
    samples = defaultdict(list)
    consumed_new_ids = set()
    for old in legacy:
        exact = new_exact.get(target_key(old), [])
        same_answer = next(
            (item for item in exact if item["answer"] == old["answer"]),
            None,
        )
        if same_answer:
            category = "retained_exact"
            consumed_new_ids.add(same_answer["question_id"])
            extra = {
                "new_answer": same_answer["answer"],
                "new_rule_id": same_answer["rule_id"],
            }
        elif exact:
            category = "changed_label"
            replacement = exact[0]
            consumed_new_ids.add(replacement["question_id"])
            extra = {
                "new_answer": replacement["answer"],
                "new_rule_id": replacement["rule_id"],
            }
        elif new_review_exact.get(target_key(old)):
            category = "newly_withheld_for_review"
            replacement = new_review_exact[target_key(old)][0]
            extra = {
                "new_answer": replacement["answer"],
                "new_rule_id": replacement["rule_id"],
                "review_reason": replacement["review_reason"],
            }
        elif new_family.get(family_key(old)):
            category = "changed_span"
            replacement = new_family[family_key(old)][0]
            consumed_new_ids.add(replacement["question_id"])
            extra = {
                "new_answer": replacement["answer"],
                "new_rule_id": replacement["rule_id"],
                "new_target_spans": replacement["target_spans"],
            }
        elif new_review_family.get(family_key(old)):
            category = "newly_withheld_for_review"
            replacement = new_review_family[family_key(old)][0]
            extra = {
                "new_answer": replacement["answer"],
                "new_rule_id": replacement["rule_id"],
                "new_target_spans": replacement["target_spans"],
                "review_reason": replacement["review_reason"],
            }
        else:
            category = "removed_no_formal_rule"
            extra = {}
        categories[category] += 1
        if len(samples[category]) < 20:
            samples[category].append(example(old, category, **extra))

    new_only = [
        item
        for item in new_accepted
        if item["question_id"] not in consumed_new_ids
    ]
    categories["newly_generated"] = len(new_only)
    samples["newly_generated"] = [
        {
            "category": "newly_generated",
            "sentence_id": item["sentence_id"],
            "dimension": item["dimension"],
            "sentence": item["sentence"],
            "target_spans": item["target_spans"],
            "new_answer": item["answer"],
            "new_rule_id": item["rule_id"],
        }
        for item in new_only[:20]
    ]
    return {
        "legacy_source_commit": "a1ed4bdc00f8888feec5a3e8923bdc03cb24c550",
        "legacy_accepted_count": len(legacy),
        "formal_accepted_count": len(new_accepted),
        "formal_review_count": sum(
            item["review_status"] == "needs-review"
            for item in new_candidates
        ),
        "category_counts": dict(sorted(categories.items())),
        "sample_limit_per_category": 20,
        "samples": dict(sorted(samples.items())),
        "comparison_notes": [
            (
                "Exact retention requires the same sentence, analysis dimension, "
                "target spans, and answer."
            ),
            (
                "Changed-span pairing is conservative: it uses the first "
                "deterministic formal candidate in the same sentence and dimension."
            ),
            (
                "The quarantined bank remains unchanged and is not a public input."
            ),
        ],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Legacy heuristic bank versus formal remap bank",
        "",
        f"- Legacy commit: `{report['legacy_source_commit']}`",
        f"- Legacy accepted questions: {report['legacy_accepted_count']}",
        f"- Formal accepted questions: {report['formal_accepted_count']}",
        f"- Formal review-only questions: {report['formal_review_count']}",
        "",
        "## Outcome counts",
        "",
    ]
    for category, count in report["category_counts"].items():
        lines.append(f"- {category.replace('_', ' ').title()}: {count}")
    lines.extend(
        [
            "",
            "The JSON companion contains up to 20 deterministic examples for "
            "each category. The comparison does not treat the old heuristic "
            "bank as a correctness oracle.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument(
        "--new-accepted", type=Path, default=DEFAULT_NEW_ACCEPTED
    )
    parser.add_argument(
        "--new-candidates", type=Path, default=DEFAULT_NEW_CANDIDATES
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        report = compare(
            list(read_jsonl(args.legacy)),
            list(read_jsonl(args.new_accepted)),
            list(read_jsonl(args.new_candidates)),
        )
        write_json(args.report, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8")
        print(
            "Compared legacy and formal banks: "
            + ", ".join(
                f"{key}={value}"
                for key, value in report["category_counts"].items()
            )
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Bank comparison failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
