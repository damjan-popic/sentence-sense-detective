#!/usr/bin/env python3
"""Create internal machine annotations with an already-installed local Stanza model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corpus_io import read_jsonl, stable_id, write_jsonl


def load_sentences(input_dir: Path) -> list[dict]:
    records = []
    for path in sorted(input_dir.glob("sentences-*.jsonl")):
        records.extend(read_jsonl(path))
    return records


def document_payload(document: object) -> dict:
    sentence_payloads = []
    for sentence in document.sentences:
        words = []
        for word in sentence.words:
            words.append(
                {
                    "id": word.id,
                    "text": word.text,
                    "lemma": word.lemma,
                    "upos": word.upos,
                    "xpos": word.xpos,
                    "head": word.head,
                    "deprel": word.deprel,
                    "start_char": word.start_char,
                    "end_char": word.end_char,
                }
            )
        sentence_payloads.append({"text": sentence.text, "words": words})
    return {"sentences": sentence_payloads}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--processors", default="tokenize,pos,lemma,depparse")
    parser.add_argument("--model", default="default")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        records = load_sentences(args.input_dir)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Pre-annotation input failed: {error}", file=sys.stderr)
        return 1
    if args.limit is not None:
        records = records[:max(0, args.limit)]
    incompatible = [record["id"] for record in records if record.get("language") != args.language]
    if incompatible:
        print(
            f"Pre-annotation stopped: {len(incompatible)} sentence(s) do not use "
            f"language={args.language}.",
            file=sys.stderr,
        )
        return 1
    if args.dry_run:
        print(
            f"Dry run: {len(records)} supplied sentences are ready for local "
            f"{args.language} pre-annotation."
        )
        print("No package, model, or resource was installed or downloaded.")
        return 0
    if args.output.exists() and not args.replace:
        print("Output exists; pass --replace only after reviewing the target.", file=sys.stderr)
        return 1
    try:
        import stanza  # type: ignore
    except ImportError:
        print(
            "Stanza is not installed. This script never installs packages or models; "
            "prepare an approved local environment first or use --dry-run.",
            file=sys.stderr,
        )
        return 2

    try:
        pipeline = stanza.Pipeline(
            lang=args.language,
            processors=args.processors,
            download_method=None,
            verbose=False,
        )
    except Exception as error:
        print(
            "The requested local model could not be opened. No download was attempted.\n"
            f"{error}",
            file=sys.stderr,
        )
        return 2

    output = []
    engine_version = getattr(stanza, "__version__", "unknown")
    for record in records:
        document = pipeline(record["text"])
        output.append(
            {
                "id": stable_id("en-ma-", record["id"], engine_version, args.processors),
                "sentence_id": record["id"],
                "language": record["language"],
                "engine": "stanza",
                "engine_version": engine_version,
                "model": args.model,
                "payload": document_payload(document),
            }
        )
    write_jsonl(args.output, output)
    print(f"Wrote {len(output)} internal machine annotations to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
