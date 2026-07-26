#!/usr/bin/env python3
"""Build conservative provisional pedagogical candidates from internal annotations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corpus_io import read_jsonl, stable_id, write_json, write_jsonl

WORD_CLASS_BY_UPOS = {
    "PROPN": "Proper noun",
    "NOUN": "Noun",
    "PRON": "Pronoun",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "DET": "Determiner",
    "VERB": "Lexical verb",
    "ADP": "Preposition",
    "CCONJ": "Coordinator",
    "SCONJ": "Subordinator",
    "INTJ": "Interjection",
    "NUM": "Numeral",
}
MODALS = {
    "can", "could", "may", "might", "must", "shall", "should", "will", "would"
}


def label_for(word: dict) -> str | None:
    upos = word.get("upos")
    if upos == "AUX":
        lemma = str(word.get("lemma") or word.get("text") or "").casefold()
        return "Modal auxiliary" if lemma in MODALS else "Auxiliary verb"
    if upos == "PART":
        return "Infinitival marker" if str(word.get("text", "")).casefold() == "to" else "Particle"
    return WORD_CLASS_BY_UPOS.get(str(upos))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", type=Path, required=True)
    parser.add_argument("--machine-annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument(
        "--dimension",
        choices=("word_class", "sentence_element", "clause_class", "marker_type",
                 "clause_structure", "clause_function"),
        default="word_class",
    )
    parser.add_argument("--max-per-sentence", type=int, default=2)
    args = parser.parse_args()
    if args.max_per_sentence < 1:
        parser.error("--max-per-sentence must be positive")
    try:
        sentences = {record["id"]: record for record in read_jsonl(args.sentences)}
        machine_records = read_jsonl(args.machine_annotations)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Candidate build failed: {error}", file=sys.stderr)
        return 1

    candidates = []
    review_queue = []
    for machine in machine_records:
        sentence = sentences.get(machine.get("sentence_id"))
        if not sentence:
            review_queue.append(
                {
                    "machine_annotation_id": machine.get("id"),
                    "reason": "missing source sentence",
                }
            )
            continue
        if args.dimension != "word_class":
            review_queue.append(
                {
                    "sentence_id": sentence["id"],
                    "machine_annotation_id": machine["id"],
                    "dimension": args.dimension,
                    "reason": "no approved automatic rule for this pedagogical dimension",
                }
            )
            continue
        token_candidates = []
        raw_sentences = machine.get("payload", {}).get("sentences", [])
        for parsed_sentence in raw_sentences:
            for word in parsed_sentence.get("words", []):
                label = label_for(word)
                start = word.get("start_char")
                end = word.get("end_char")
                if not label:
                    continue
                if (
                    not isinstance(start, int)
                    or not isinstance(end, int)
                    or start < 0
                    or end <= start
                    or end > len(sentence["text"])
                    or sentence["text"][start:end] != word.get("text")
                ):
                    review_queue.append(
                        {
                            "sentence_id": sentence["id"],
                            "machine_annotation_id": machine["id"],
                            "token": word.get("text"),
                            "reason": "missing or invalid character offsets",
                        }
                    )
                    continue
                question_id = stable_id(
                    "POS-AUTO-",
                    sentence["id"],
                    start,
                    end,
                    label,
                    length=12,
                )
                token_candidates.append(
                    {
                        "id": stable_id("en-pa-", question_id),
                        "sentence_id": sentence["id"],
                        "language": sentence["language"],
                        "mode": "parts-of-speech",
                        "subskill": "Parts of speech",
                        "dimension": "word_class",
                        "target_spans": [{"start": start, "end": end}],
                        "label": label,
                        "review_status": "provisional",
                        "source_question_id": question_id,
                    }
                )
        candidates.extend(token_candidates[:args.max_per_sentence])

    write_jsonl(args.output, candidates)
    write_json(
        args.review_queue,
        {
            "candidate_count": len(candidates),
            "manual_review_count": len(review_queue),
            "items": review_queue,
        },
    )
    print(
        f"Wrote {len(candidates)} provisional candidates; "
        f"{len(review_queue)} items require manual review."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
