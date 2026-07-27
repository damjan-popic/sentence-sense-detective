#!/usr/bin/env python3
"""Turn materialised pedagogical-remap records into deterministic questions.

This module is intentionally presentation-only. It does not inspect UD/Stanza
graphs or decide pedagogical labels; those decisions belong to the formal
remapping stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from pipeline_common import ROOT, read_json, read_jsonl, write_json, write_jsonl

DEFAULT_SENTENCES = ROOT / "data" / "corpus" / "sentences_10k.jsonl"
DEFAULT_REMAPPED = (
    ROOT / "data" / "remap" / "en" / "pedagogical_candidates_10k.jsonl.gz"
)
DEFAULT_TAGSET = ROOT / "config" / "pedagogical_tagset_en.json"
OUTPUT_ROOT = ROOT / "data" / "generated"
DEFAULT_CANDIDATES = OUTPUT_ROOT / "question_candidates.jsonl.gz"
DEFAULT_ACCEPTED = OUTPUT_ROOT / "accepted_questions.jsonl.gz"
DEFAULT_REJECTED = OUTPUT_ROOT / "rejected_questions.jsonl"
DEFAULT_PRIMARY = OUTPUT_ROOT / "sentence_primary_questions.json"
DEFAULT_REPORT = OUTPUT_ROOT / "generation_report.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "question_generation_report.md"


def stable_digest(*values: object) -> str:
    return hashlib.sha256(
        "\0".join(str(value) for value in values).encode("utf-8")
    ).hexdigest()


def contiguous_span(words: list[dict]) -> dict | None:
    ordered = sorted(
        (
            word
            for word in words
            if isinstance(word.get("start_char"), int)
            and isinstance(word.get("end_char"), int)
        ),
        key=lambda word: (word["start_char"], word["end_char"]),
    )
    while ordered and ordered[0].get("upos") == "PUNCT":
        ordered.pop(0)
    while ordered and ordered[-1].get("upos") == "PUNCT":
        ordered.pop()
    if not ordered:
        return None
    return {
        "start": min(word["start_char"] for word in ordered),
        "end": max(word["end_char"] for word in ordered),
    }


def options_for(answer: str, dimension: str, tagset: dict, question_key: str) -> list[str]:
    labels = tagset["dimensions"][dimension]["labels"]
    if answer not in labels:
        raise ValueError(f"{answer!r} is outside controlled dimension {dimension}")
    distractors = sorted(
        (label for label in labels if label != answer),
        key=lambda label: stable_digest(question_key, label),
    )
    if len(distractors) < 3:
        raise ValueError(f"{dimension} does not provide three distractors")
    return [answer, *distractors[:3]]


def question(
    *,
    sentence: dict,
    dimension: str,
    target: dict | None = None,
    target_spans: list[dict] | None = None,
    answer: str,
    prompt: str,
    explanation: str,
    confidence: float,
    rule_id: str,
    review_status: str,
    tagset: dict,
    review_reason: str | None = None,
    reference_case_ids: list[str] | None = None,
    provenance: dict | None = None,
) -> dict:
    spans = target_spans if target_spans is not None else ([target] if target else [])
    key = (
        f"{sentence['sentence_id']}:{dimension}:"
        f"{json.dumps(spans, separators=(',', ':'))}:"
        f"{answer}:{rule_id}"
    )
    identifier = f"AUTO-{dimension.upper().replace('_', '-')}-{stable_digest(key)[:16]}"
    record = {
        "question_id": identifier,
        "sentence_id": sentence["sentence_id"],
        "genre": sentence["source"]["genre"],
        "source_corpus": sentence["source"]["corpus"],
        "sentence": sentence["text"],
        "target_spans": spans,
        "mode": tagset["dimensions"][dimension]["mode"],
        "subskill": tagset["dimensions"][dimension]["subskill"],
        "dimension": dimension,
        "prompt": prompt,
        "answer": answer,
        "options": options_for(answer, dimension, tagset, key),
        "explanation": explanation,
        "difficulty": sentence["selection"]["difficulty"],
        "confidence": confidence,
        "rule_id": rule_id,
        "review_status": review_status,
        "review_reason": review_reason,
        "reference_case_ids": reference_case_ids or [],
    }
    if provenance:
        record.update(provenance)
    return record


def internal_provenance(item: dict) -> dict:
    return {
        key: item[key]
        for key in (
            "remap_profile",
            "remap_profile_sha256",
            "remap_rule_id",
            "decision_class",
            "action",
            "source_case_ids",
            "matched_evidence",
            "stanza_version",
            "model_bundle_sha256",
            "remap_candidate_id",
        )
        if key in item
    }


def questions_from_remap(
    sentence: dict,
    remapped_items: list[dict],
    tagset: dict,
) -> list[dict]:
    prompts = {
        "word_class": "Which part of speech is the highlighted word?",
        "sentence_element": "What is the function of the highlighted word or phrase?",
        "clause_type": "Which description best fits the highlighted clause?",
        "clause_marker": "What type of clause marker is highlighted?",
        "clause_structure": "What is the structure of the highlighted clause?",
        "clause_function": "What function does the highlighted clause have in the larger sentence?",
    }
    questions = [
        question(
            sentence=sentence,
            dimension=item["dimension"],
            target_spans=item["target_spans"],
            answer=item["answer"],
            prompt=prompts[item["dimension"]],
            explanation=item["explanation"],
            confidence=item["confidence"],
            rule_id=item["rule_id"],
            review_status=item["review_status"],
            review_reason=item["review_reason"],
            reference_case_ids=item["reference_case_ids"],
            provenance=internal_provenance(item),
            tagset=tagset,
        )
        for item in remapped_items
    ]
    word_class = [
        item for item in questions if item["dimension"] == "word_class"
    ]
    other_dimensions = [
        item for item in questions if item["dimension"] != "word_class"
    ]
    basis = sentence["selection"]["primary_pos_candidate"]
    basis_span = {"start": basis["start"], "end": basis["end"]}
    word_class.sort(
        key=lambda item: (
            0
            if item["target_spans"] == [basis_span]
            and item["answer"] == basis["label"]
            else 1,
            stable_digest(item["question_id"]),
        )
    )
    other_dimensions.sort(key=lambda item: item["question_id"])
    return [*word_class[:2], *other_dimensions]


def validate_candidate(candidate: dict) -> str | None:
    options = candidate["options"]
    if len(options) != 4 or len(set(options)) != 4:
        return "options_not_four_unique"
    if candidate["answer"] not in options:
        return "answer_missing_from_options"
    sentence = candidate["sentence"]
    spans = candidate["target_spans"]
    if not spans:
        return "missing_target"
    if (
        candidate["review_status"] == "needs-review"
        and not candidate.get("review_reason")
    ):
        return "missing_review_reason"
    previous_end = -1
    for span in spans:
        if not (
            isinstance(span["start"], int)
            and isinstance(span["end"], int)
            and 0 <= span["start"] < span["end"] <= len(sentence)
        ):
            return "invalid_target_offsets"
        if span["start"] < previous_end:
            return "overlapping_or_unsorted_targets"
        previous_end = span["end"]
    return None


def generate(
    sentences: list[dict],
    remapped: list[dict],
    tagset: dict,
):
    sentence_ids = {sentence["sentence_id"] for sentence in sentences}
    remapped_by_id: dict[str, list[dict]] = {
        sentence_id: [] for sentence_id in sentence_ids
    }
    for record in remapped:
        sentence_id = record["sentence_id"]
        if sentence_id not in remapped_by_id:
            raise ValueError(
                f"{sentence_id}: remap record does not belong to the selected corpus"
            )
        remapped_by_id[sentence_id].append(record)
    candidates = []
    rejected = []
    primary = {}
    for index, sentence in enumerate(sentences, 1):
        generated = questions_from_remap(
            sentence,
            remapped_by_id[sentence["sentence_id"]],
            tagset,
        )
        accepted_for_sentence = []
        for candidate in generated:
            reason = validate_candidate(candidate)
            if reason:
                rejected.append({**candidate, "review_status": "rejected", "rejection_reason": reason})
            else:
                candidates.append(candidate)
                if candidate["review_status"] == "auto-high-confidence":
                    accepted_for_sentence.append(candidate)
        if not accepted_for_sentence:
            raise ValueError(
                f"{sentence['sentence_id']}: no accepted question survived generation"
            )
        primary[sentence["sentence_id"]] = accepted_for_sentence[0]["question_id"]
        if index % 1000 == 0:
            print(f"Generated candidates for {index}/{len(sentences)} sentences.", flush=True)
    candidates.sort(key=lambda item: item["question_id"])
    accepted = [
        candidate
        for candidate in candidates
        if candidate["review_status"] in {"auto-high-confidence", "human-reviewed"}
    ]
    rejected.sort(key=lambda item: item["question_id"])
    return candidates, accepted, rejected, primary


def build_report(
    sentences: list[dict],
    candidates: list[dict],
    accepted: list[dict],
    rejected: list[dict],
) -> dict:
    question_counts = Counter(candidate["sentence_id"] for candidate in accepted)
    grouped = Counter(
        "1" if count == 1 else "2" if count == 2 else "3+"
        for count in question_counts.values()
    )
    return {
        "sentence_count": len(sentences),
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "review_needed_count": sum(
            candidate["review_status"] == "needs-review" for candidate in candidates
        ),
        "rejected_count": len(rejected),
        "accepted_by_mode": dict(
            sorted(Counter(candidate["mode"] for candidate in accepted).items())
        ),
        "accepted_by_dimension": dict(
            sorted(Counter(candidate["dimension"] for candidate in accepted).items())
        ),
        "accepted_by_label": dict(
            sorted(Counter(candidate["answer"] for candidate in accepted).items())
        ),
        "candidate_status_counts": dict(
            sorted(Counter(candidate["review_status"] for candidate in candidates).items())
        ),
        "review_needed_by_rule": dict(
            sorted(
                Counter(
                    candidate["rule_id"]
                    for candidate in candidates
                    if candidate["review_status"] == "needs-review"
                ).items()
            )
        ),
        "review_needed_by_reason": dict(
            sorted(
                Counter(
                    candidate["review_reason"]
                    for candidate in candidates
                    if candidate["review_status"] == "needs-review"
                ).items()
            )
        ),
        "non_highlightable_contract_cases": {
            "CL-MARK-10": (
                "Zero marker is retained in the reviewed core, but no synthetic "
                "∅ character is inserted into unchanged corpus sentences."
            )
        },
        "questions_per_sentence": {
            bucket: {
                "sentences": grouped[bucket],
                "percentage": round(grouped[bucket] / len(sentences) * 100, 2),
            }
            for bucket in ("1", "2", "3+")
        },
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Question-generation report",
        "",
        f"- Corpus sentences: {report['sentence_count']}",
        f"- Generated candidates: {report['candidate_count']}",
        f"- Accepted questions: {report['accepted_count']}",
        f"- Needs review: {report['review_needed_count']}",
        f"- Rejected questions: {report['rejected_count']}",
        "",
        "## Accepted questions by mode",
        "",
    ]
    for mode, count in report["accepted_by_mode"].items():
        lines.append(f"- {mode}: {count}")
    lines.extend(["", "## Accepted questions by analysis dimension", ""])
    for dimension, count in report["accepted_by_dimension"].items():
        lines.append(f"- {dimension}: {count}")
    lines.extend(["", "## Review queue by rule", ""])
    for rule_id, count in report["review_needed_by_rule"].items():
        lines.append(f"- {rule_id}: {count}")
    lines.extend(["", "## Accepted questions per sentence", ""])
    for bucket, values in report["questions_per_sentence"].items():
        lines.append(
            f"- {bucket}: {values['sentences']} ({values['percentage']}%)"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", type=Path, default=DEFAULT_SENTENCES)
    parser.add_argument("--remapped", type=Path, default=DEFAULT_REMAPPED)
    parser.add_argument("--tagset", type=Path, default=DEFAULT_TAGSET)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--accepted", type=Path, default=DEFAULT_ACCEPTED)
    parser.add_argument("--rejected", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--primary-index", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        sentences = list(read_jsonl(args.sentences))
        candidates, accepted, rejected, primary = generate(
            sentences,
            list(read_jsonl(args.remapped)),
            read_json(args.tagset),
        )
        write_jsonl(args.candidates, candidates)
        write_jsonl(args.accepted, accepted)
        write_jsonl(args.rejected, rejected)
        write_json(args.primary_index, primary)
        report = build_report(sentences, candidates, accepted, rejected)
        write_json(args.report, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_report(report), encoding="utf-8")
        print(
            f"Generated {len(candidates)} candidates: {len(accepted)} accepted, "
            f"{report['review_needed_count']} needing review, {len(rejected)} rejected."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Question generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
