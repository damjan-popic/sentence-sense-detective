#!/usr/bin/env python3
"""Validate and shard a supplied, rights-cleared TSV or JSONL sentence corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from corpus_io import BCP47, sha256_file, write_json, write_jsonl

REQUIRED_INPUT_FIELDS = (
    "sentence_id",
    "language",
    "text",
    "source_id",
    "licence",
    "attribution",
)
DEFAULT_SHARD_SIZE = 500


def read_input(path: Path) -> list[dict[str, str]]:
    if path.suffix.casefold() == ".tsv":
        with path.open(encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]
    if path.suffix.casefold() == ".jsonl":
        records = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            records.append({key: "" if val is None else str(val) for key, val in value.items()})
        return records
    raise ValueError("Input must use .tsv or .jsonl")


def near_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(character for character in normalized if character.isalnum())


def validate_and_transform(rows: list[dict[str, str]]) -> tuple[list[dict], dict]:
    errors = []
    ids = set()
    exact_groups: dict[str, list[str]] = defaultdict(list)
    near_groups: dict[str, list[str]] = defaultdict(list)
    records = []
    for index, row in enumerate(rows, 2):
        missing = [field for field in REQUIRED_INPUT_FIELDS if not str(row.get(field, "")).strip()]
        if missing:
            errors.append(f"row {index}: missing {', '.join(missing)}")
            continue
        sentence_id = row["sentence_id"].strip()
        if sentence_id in ids:
            errors.append(f"row {index}: duplicate sentence_id {sentence_id!r}")
            continue
        ids.add(sentence_id)
        language = row["language"].strip()
        if not BCP47.fullmatch(language):
            errors.append(f"row {index}: invalid BCP 47 language {language!r}")
            continue
        text = row["text"]
        if "\r" in text or "\n" in text:
            errors.append(f"row {index}: sentence text must occupy one record")
            continue
        exact_groups[text].append(sentence_id)
        near_groups[near_key(text)].append(sentence_id)
        records.append(
            {
                "id": sentence_id,
                "language": language,
                "text": text,
                "source": {
                    "source_id": row["source_id"].strip(),
                    "document_id": row.get("document_id", "").strip() or None,
                    "licence": row["licence"].strip(),
                    "attribution": row["attribution"].strip(),
                },
                "pedagogical_annotations": [],
                "review_status": "provisional",
            }
        )
    if errors:
        raise ValueError("\n".join(errors))

    exact_duplicates = [
        {"text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "sentence_ids": values}
        for text, values in exact_groups.items()
        if len(values) > 1
    ]
    exact_duplicate_ids = {
        sentence_id
        for group in exact_duplicates
        for sentence_id in group["sentence_ids"]
    }
    near_duplicates = [
        {"fingerprint": key, "sentence_ids": values}
        for key, values in near_groups.items()
        if key and len(values) > 1 and not set(values).issubset(exact_duplicate_ids)
    ]
    audit = {
        "input_records": len(rows),
        "accepted_records": len(records),
        "exact_duplicate_groups": exact_duplicates,
        "near_duplicate_groups": near_duplicates,
    }
    return records, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="rights-cleared .tsv or .jsonl input")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=DEFAULT_SHARD_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.shard_size < 1 or args.shard_size > 500:
        parser.error("--shard-size must be between 1 and 500")
    try:
        records, audit = validate_and_transform(read_input(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Ingestion failed:\n{error}", file=sys.stderr)
        return 1
    audit["input_path"] = args.input.name
    audit["input_sha256"] = sha256_file(args.input)
    audit["dry_run"] = args.dry_run
    if args.dry_run:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 0

    existing = sorted(args.output_dir.glob("sentences-*.jsonl"))
    if existing and not args.replace:
        print(
            f"Ingestion refused to overwrite {len(existing)} existing shard(s); "
            "use --replace only after reviewing the target.",
            file=sys.stderr,
        )
        return 1
    if args.replace:
        for path in existing:
            path.unlink()

    shard_entries = []
    for start in range(0, len(records), args.shard_size):
        shard = records[start:start + args.shard_size]
        path = args.output_dir / f"sentences-{start // args.shard_size + 1:04d}.jsonl"
        write_jsonl(path, shard)
        shard_entries.append(
            {
                "path": path.name,
                "count": len(shard),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "sentence_count": len(records),
        "shard_size": args.shard_size,
        "shards": shard_entries,
    }
    write_json(args.output_dir / "manifest.json", manifest)
    write_json(args.output_dir / "ingestion-audit.json", audit)
    print(f"Ingested {len(records)} supplied sentences into {len(shard_entries)} shard(s).")
    print(
        f"Exact duplicate groups: {len(audit['exact_duplicate_groups'])}; "
        f"near duplicate groups: {len(audit['near_duplicate_groups'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
