#!/usr/bin/env python3
"""Report formal-rule use and output distributions over the selected 10K."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from pipeline_common import ROOT, read_jsonl, write_json

DEFAULT_SENTENCES = ROOT / "data/corpus/sentences_10k.jsonl"
DEFAULT_REMAPPED = ROOT / "data/remap/en/pedagogical_candidates_10k.jsonl.gz"
DEFAULT_PROFILE = ROOT / "data/remap/en/compiled_rules.json"
DEFAULT_QUESTIONS = ROOT / "data/generated/question_candidates.jsonl.gz"
DEFAULT_REPORT = ROOT / "reports/remap_rule_distribution.json"
DEFAULT_MARKDOWN = ROOT / "reports/remap_rule_distribution.md"


def counter(values) -> dict:
    return dict(sorted(Counter(values).items()))


def build(
    sentences: list[dict],
    remapped: list[dict],
    profile: dict,
    questions: list[dict],
) -> dict:
    sentence_by_id = {
        sentence["sentence_id"]: sentence for sentence in sentences
    }
    actual_by_rule = Counter(item["remap_rule_id"] for item in remapped)
    publish_by_rule = Counter(
        item["remap_rule_id"]
        for item in remapped
        if item["action"] == "publish"
    )
    review_by_rule = Counter(
        item["remap_rule_id"]
        for item in remapped
        if item["action"] == "review"
    )
    conflict_by_rule = Counter(
        item["remap_rule_id"]
        for item in remapped
        if str(item.get("review_reason") or "").startswith(
            "Incompatible formal rules"
        )
    )
    rule_rows = []
    for rule in profile["rules"]:
        rule_id = rule["rule_id"]
        rule_rows.append(
            {
                "rule_id": rule_id,
                "dimension": rule["dimension"],
                "configured_action": rule["action"],
                "decision_class": rule["decision_class"],
                "source_case_ids": rule["source_case_ids"],
                "matched_10k": actual_by_rule[rule_id],
                "published_10k": publish_by_rule[rule_id],
                "reviewed_10k": review_by_rule[rule_id],
                "conflict_downgrades_10k": conflict_by_rule[rule_id],
            }
        )
    review_items = [
        item for item in remapped if item["action"] == "review"
    ]
    return {
        "profile_id": profile["profile_id"],
        "profile_sha256": profile["profile_sha256"],
        "sentence_count": len(sentences),
        "formal_candidate_count": len(remapped),
        "presented_candidate_count": len(questions),
        "publish_count": sum(
            item["action"] == "publish" for item in remapped
        ),
        "review_count": len(review_items),
        "conflict_downgrade_count": sum(conflict_by_rule.values()),
        "rules_with_matches": sum(row["matched_10k"] > 0 for row in rule_rows),
        "rules_without_matches": sum(
            row["matched_10k"] == 0 for row in rule_rows
        ),
        "by_action": counter(item["action"] for item in remapped),
        "by_decision_class": counter(
            item["decision_class"] for item in remapped
        ),
        "by_dimension": counter(item["dimension"] for item in remapped),
        "by_label": counter(item["answer"] for item in remapped),
        "by_genre": counter(
            sentence_by_id[item["sentence_id"]]["source"]["genre"]
            for item in remapped
        ),
        "by_difficulty": counter(
            sentence_by_id[item["sentence_id"]]["selection"]["difficulty"]
            for item in remapped
        ),
        "by_source_corpus": counter(
            sentence_by_id[item["sentence_id"]]["source"]["corpus"]
            for item in remapped
        ),
        "review_by_reason": counter(
            item["review_reason"] for item in review_items
        ),
        "rules": rule_rows,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Formal remap rule distribution",
        "",
        f"- Profile: `{report['profile_id']}`",
        f"- Sentences: {report['sentence_count']}",
        f"- Formal candidates before presentation selection: "
        f"{report['formal_candidate_count']}",
        f"- Presented question candidates: {report['presented_candidate_count']}",
        f"- Publishable formal candidates: {report['publish_count']}",
        f"- Review-only formal candidates: {report['review_count']}",
        f"- Conflict downgrades: {report['conflict_downgrade_count']}",
        f"- Rules with at least one 10K match: {report['rules_with_matches']}",
        f"- Rules without a 10K match: {report['rules_without_matches']}",
        "",
        "## Per-rule counts",
        "",
        "| Rule | Dimension | Decision | Configured action | Matches | Publish | Review | Conflicts |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in report["rules"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['rule_id']}`",
                    row["dimension"],
                    row["decision_class"],
                    row["configured_action"],
                    str(row["matched_10k"]),
                    str(row["published_10k"]),
                    str(row["reviewed_10k"]),
                    str(row["conflict_downgrades_10k"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", type=Path, default=DEFAULT_SENTENCES)
    parser.add_argument("--remapped", type=Path, default=DEFAULT_REMAPPED)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        report = build(
            list(read_jsonl(args.sentences)),
            list(read_jsonl(args.remapped)),
            json.loads(args.profile.read_text(encoding="utf-8")),
            list(read_jsonl(args.questions)),
        )
        write_json(args.report, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8")
        print(
            f"Reported {len(report['rules'])} formal rules: "
            f"{report['rules_with_matches']} matched the 10K."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Remap distribution report failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
