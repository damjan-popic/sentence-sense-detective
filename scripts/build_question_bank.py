#!/usr/bin/env python3
"""Build provisional questions and support file-based human review."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from pathlib import Path

from corpus_io import read_jsonl, write_json, write_jsonl

PROMPT_BY_DIMENSION = {
    "word_class": "Which part of speech is the highlighted word?",
}
OPTIONS_BY_LABEL = {
    "Proper noun": ["Proper noun", "Noun", "Pronoun", "Adjective"],
    "Noun": ["Noun", "Proper noun", "Pronoun", "Adjective"],
    "Pronoun": ["Pronoun", "Determiner", "Noun", "Proper noun"],
    "Adjective": ["Adjective", "Adverb", "Noun", "Determiner"],
    "Adverb": ["Adverb", "Adjective", "Preposition", "Particle"],
    "Determiner": ["Determiner", "Pronoun", "Adjective", "Preposition"],
    "Lexical verb": ["Lexical verb", "Auxiliary verb", "Modal auxiliary", "Adjective"],
    "Auxiliary verb": ["Auxiliary verb", "Modal auxiliary", "Lexical verb", "Particle"],
    "Modal auxiliary": ["Modal auxiliary", "Auxiliary verb", "Lexical verb", "Adverb"],
    "Preposition": ["Preposition", "Particle", "Subordinator", "Infinitival marker"],
    "Particle": ["Particle", "Preposition", "Adverb", "Infinitival marker"],
    "Subordinator": ["Subordinator", "Coordinator", "Preposition", "Adverb"],
    "Coordinator": ["Coordinator", "Subordinator", "Preposition", "Adverb"],
    "Infinitival marker": ["Infinitival marker", "Preposition", "Subordinator", "Particle"],
    "Interjection": ["Interjection", "Adverb", "Noun", "Coordinator"],
    "Numeral": ["Numeral", "Noun", "Determiner", "Adjective"],
}
EXPLANATION_BY_LABEL = {
    "Proper noun": "The highlighted word is an individual name, so it is a proper noun.",
    "Noun": "The highlighted word names a person, place, thing, or concept, so it is a noun.",
    "Pronoun": "The highlighted word stands in for a noun phrase, so it is a pronoun.",
    "Adjective": "The highlighted word describes a noun or completes an adjectival description.",
    "Adverb": "The highlighted word modifies an action, description, or circumstance.",
    "Determiner": "The highlighted word introduces or specifies a noun phrase.",
    "Lexical verb": "The highlighted word expresses the main action, event, or state.",
    "Auxiliary verb": "The highlighted word helps form the verb phrase.",
    "Modal auxiliary": "The highlighted word expresses meanings such as possibility, necessity, or prediction.",
    "Preposition": "The highlighted word heads a phrase expressing a relation such as place or direction.",
    "Particle": "The highlighted word combines with a verb as part of a multi-word verb.",
    "Subordinator": "The highlighted word introduces a subordinate clause.",
    "Coordinator": "The highlighted word joins units of equal grammatical status.",
    "Infinitival marker": "The highlighted “to” introduces an infinitive.",
    "Interjection": "The highlighted word is a self-contained expression of reaction or attitude.",
    "Numeral": "The highlighted word expresses a number or quantity.",
}


def build_questions(sentences_path: Path, annotations_path: Path) -> list[dict]:
    sentences = {record["id"]: record for record in read_jsonl(sentences_path)}
    output = []
    for annotation in read_jsonl(annotations_path):
        if annotation["review_status"] != "provisional":
            continue
        label = annotation["label"]
        options = OPTIONS_BY_LABEL.get(label)
        prompt = PROMPT_BY_DIMENSION.get(annotation["dimension"])
        if not options or not prompt:
            raise ValueError(
                f"{annotation['id']}: no approved question template for "
                f"{annotation['dimension']} / {label}"
            )
        sentence = sentences.get(annotation["sentence_id"])
        if not sentence:
            raise ValueError(f"{annotation['id']}: missing sentence {annotation['sentence_id']}")
        output.append(
            {
                "id": annotation["source_question_id"],
                "source_id": sentence["source"]["source_id"],
                "sentence_id": sentence["id"],
                "annotation_id": annotation["id"],
                "language": sentence["language"],
                "mode": annotation["mode"],
                "subskill": annotation["subskill"],
                "prompt": prompt,
                "answer": label,
                "options": options,
                "explanation": EXPLANATION_BY_LABEL[label],
                "review_status": "provisional",
            }
        )
    return output


def export_review(
    questions_path: Path,
    annotations_path: Path,
    sentences_path: Path,
    output_path: Path,
) -> None:
    annotations = {record["id"]: record for record in read_jsonl(annotations_path)}
    sentences = {record["id"]: record for record in read_jsonl(sentences_path)}
    rows = []
    for question in read_jsonl(questions_path):
        annotation = annotations[question["annotation_id"]]
        rows.append(
            {
                "id": question["id"],
                "sentence_id": question["sentence_id"],
                "annotation_id": question["annotation_id"],
                "source_id": question["source_id"],
                "sentence": sentences[question["sentence_id"]]["text"],
                "target_spans": json.dumps(annotation["target_spans"], ensure_ascii=False),
                "prompt": question["prompt"],
                "answer": question["answer"],
                "options": json.dumps(question["options"], ensure_ascii=False),
                "explanation": question["explanation"],
                "review_status": question["review_status"],
                "rationale": "",
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.casefold() == ".tsv":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [
                "id", "sentence_id", "annotation_id", "source_id", "sentence",
                "target_spans", "prompt", "answer", "options", "explanation",
                "review_status", "rationale",
            ], delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
    else:
        write_jsonl(output_path, rows)


def read_corrections(path: Path) -> list[dict]:
    if path.suffix.casefold() == ".tsv":
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    else:
        rows = read_jsonl(path)
    parsed = []
    for row in rows:
        value = dict(row)
        for field in ("options", "target_spans"):
            if field in value and isinstance(value[field], str) and value[field].strip():
                value[field] = json.loads(value[field])
        parsed.append(value)
    return parsed


def apply_corrections(
    questions: list[dict],
    annotations: list[dict],
    corrections: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    question_by_id = {record["id"]: record for record in questions}
    annotation_by_id = {record["id"]: record for record in annotations}
    changes = []
    allowed_question_fields = ("prompt", "answer", "options", "explanation", "review_status")
    for correction in corrections:
        question_id = correction.get("id")
        if question_id not in question_by_id:
            raise ValueError(f"Unknown question ID {question_id!r}")
        question = question_by_id[question_id]
        annotation = annotation_by_id[question["annotation_id"]]
        proposed = {}
        for field in allowed_question_fields:
            if field in correction and correction[field] not in ("", None):
                proposed[field] = correction[field]
        if "target_spans" in correction and correction["target_spans"] not in ("", None):
            proposed["target_spans"] = correction["target_spans"]
        changed = {
            field: {
                "before": annotation["target_spans"] if field == "target_spans" else question[field],
                "after": value,
            }
            for field, value in proposed.items()
            if (annotation["target_spans"] if field == "target_spans" else question[field]) != value
        }
        if not changed:
            continue
        if question["review_status"] == "teacher-reviewed":
            raise ValueError(
                f"{question_id}: reviewed-core changes require the project-level "
                "rationale, implementation-log, and regression-test workflow"
            )
        rationale = str(correction.get("rationale", "")).strip()
        if not rationale:
            raise ValueError(f"{question_id}: every correction requires a rationale")
        new_status = proposed.get("review_status", question["review_status"])
        if new_status not in {"provisional", "teacher-reviewed"}:
            raise ValueError(f"{question_id}: invalid review_status {new_status!r}")
        if "options" in proposed:
            if len(proposed["options"]) != 4 or len(set(proposed["options"])) != 4:
                raise ValueError(f"{question_id}: options must contain four unique values")
        final_answer = proposed.get("answer", question["answer"])
        final_options = proposed.get("options", question["options"])
        if final_answer not in final_options:
            raise ValueError(f"{question_id}: corrected options omit the answer")
        for field, value in proposed.items():
            if field == "target_spans":
                annotation["target_spans"] = value
            else:
                question[field] = value
        annotation["label"] = question["answer"]
        annotation["review_status"] = question["review_status"]
        changes.append(
            {
                "question_id": question_id,
                "rationale": rationale,
                "changes": changed,
            }
        )
    return questions, annotations, changes


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--sentences", type=Path, required=True)
    build.add_argument("--annotations", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)

    export = subparsers.add_parser("export-review")
    export.add_argument("--questions", type=Path, required=True)
    export.add_argument("--annotations", type=Path, required=True)
    export.add_argument("--sentences", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)

    apply = subparsers.add_parser("apply-corrections")
    apply.add_argument("--questions", type=Path, required=True)
    apply.add_argument("--annotations", type=Path, required=True)
    apply.add_argument("--corrections", type=Path, required=True)
    apply.add_argument("--questions-output", type=Path, required=True)
    apply.add_argument("--annotations-output", type=Path, required=True)
    apply.add_argument("--change-report", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "build":
            questions = build_questions(args.sentences, args.annotations)
            write_jsonl(args.output, questions)
            print(f"Wrote {len(questions)} provisional questions.")
        elif args.command == "export-review":
            export_review(args.questions, args.annotations, args.sentences, args.output)
            print(f"Wrote review export to {args.output}.")
        else:
            questions, annotations, changes = apply_corrections(
                copy.deepcopy(read_jsonl(args.questions)),
                copy.deepcopy(read_jsonl(args.annotations)),
                read_corrections(args.corrections),
            )
            write_jsonl(args.questions_output, questions)
            write_jsonl(args.annotations_output, annotations)
            write_json(
                args.change_report,
                {
                    "applied_change_count": len(changes),
                    "changes": changes,
                },
            )
            print(f"Applied {len(changes)} reviewed correction(s).")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Question-bank operation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
