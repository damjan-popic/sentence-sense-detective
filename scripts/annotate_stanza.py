#!/usr/bin/env python3
"""Annotate the selected 10K sentences with a resumable local Stanza pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline_common import ROOT, canonical_json_bytes, read_jsonl, write_json
from stanza_support import (
    MODEL_REPORT,
    PROCESSORS,
    download_models,
    ensure_models,
    load_pipeline,
    word_record,
)

DEFAULT_INPUT = ROOT / "data" / "corpus" / "sentences_10k.jsonl"
DEFAULT_JSONL = ROOT / "data" / "corpus" / "sentences_10k.annotations.jsonl"
DEFAULT_CONLLU = ROOT / "data" / "corpus" / "sentences_10k.conllu"
DEFAULT_BATCHES = ROOT / "external" / "annotation_batches" / "en"
DEFAULT_REPORT = ROOT / "reports" / "annotation_report.json"


def space_after_misc(words: list, index: int) -> str:
    word = words[index]
    values = [
        f"StartChar={word['start_char']}",
        f"EndChar={word['end_char']}",
    ]
    if index + 1 < len(words) and word["end_char"] == words[index + 1]["start_char"]:
        values.append("SpaceAfter=No")
    return "|".join(values)


def conllu_record(sentence_id: str, text: str, words: list[dict]) -> str:
    lines = [f"# sent_id = {sentence_id}", f"# text = {text.replace(chr(10), ' ')}"]
    for index, word in enumerate(words):
        lines.append(
            "\t".join(
                [
                    str(word["id"]),
                    word["text"] or "_",
                    word["lemma"] or "_",
                    word["upos"] or "_",
                    word["xpos"] or "_",
                    word["feats"] or "_",
                    str(word["head"]) if word["head"] is not None else "_",
                    word["deprel"] or "_",
                    "_",
                    space_after_misc(words, index),
                ]
            )
        )
    return "\n".join(lines) + "\n\n"


def process_one(annotated, source: dict, model: dict, *, gpu_used: bool) -> tuple[dict, str]:
    if len(annotated.sentences) != 1:
        raise ValueError(
            f"{source['sentence_id']}: selected sentence split into "
            f"{len(annotated.sentences)} units during final annotation"
        )
    sentence = annotated.sentences[0]
    words = [word_record(word) for word in sentence.words]
    for word in words:
        start, end = word["start_char"], word["end_char"]
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source["text"])
            or source["text"][start:end] != word["text"]
        ):
            raise ValueError(
                f"{source['sentence_id']}: token offsets do not align for {word['text']!r}"
            )
    record = {
        "sentence_id": source["sentence_id"],
        "text": source["text"],
        "tokens": words,
        "annotation": {
            "engine": "stanza",
            "stanza_version": model["stanza_version"],
            "package": model["package"],
            "model_bundle_sha256": model["model_bundle_sha256"],
            "processors": list(PROCESSORS),
            "gpu_used": gpu_used,
        },
    }
    return record, conllu_record(source["sentence_id"], source["text"], words)


def annotate(
    input_path: Path,
    jsonl_path: Path,
    conllu_path: Path,
    batches_root: Path,
    report_path: Path,
    *,
    batch_size: int,
    use_gpu: bool,
) -> dict:
    sources = list(read_jsonl(input_path))
    model = ensure_models()
    nlp, gpu_used = load_pipeline(
        PROCESSORS, use_gpu=use_gpu, no_sentence_split=True
    )
    batches_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed = 0
    for batch_start in range(0, len(sources), batch_size):
        batch = sources[batch_start:batch_start + batch_size]
        batch_number = batch_start // batch_size
        json_batch = batches_root / f"batch-{batch_number:04d}.jsonl"
        conllu_batch = batches_root / f"batch-{batch_number:04d}.conllu"
        marker = batches_root / f"batch-{batch_number:04d}.done.json"
        expected_ids = [source["sentence_id"] for source in batch]
        input_sha256 = hashlib.sha256(
            canonical_json_bytes(
                [
                    {"sentence_id": source["sentence_id"], "text": source["text"]}
                    for source in batch
                ]
            )
        ).hexdigest()
        if marker.exists() and json_batch.exists() and conllu_batch.exists():
            state = json.loads(marker.read_text(encoding="utf-8"))
            if (
                state.get("sentence_ids") == expected_ids
                and state.get("model_bundle_sha256") == model["model_bundle_sha256"]
                and state.get("input_sha256") in {None, input_sha256}
            ):
                if state.get("input_sha256") is None:
                    state["input_sha256"] = input_sha256
                    write_json(marker, state)
                completed += len(batch)
                print(f"Reused annotation batch {batch_number:04d}.", flush=True)
                continue
            print(
                f"Refreshing annotation batch {batch_number:04d} because its "
                "input or model fingerprint changed.",
                flush=True,
            )
        json_content = bytearray()
        conllu_content = []
        annotated_batch = nlp.bulk_process([source["text"] for source in batch])
        if len(annotated_batch) != len(batch):
            raise ValueError(
                f"annotation batch {batch_number:04d} returned an unexpected document count"
            )
        for source, annotated in zip(batch, annotated_batch, strict=True):
            record, conllu = process_one(
                annotated, source, model, gpu_used=gpu_used
            )
            json_content.extend(canonical_json_bytes(record))
            conllu_content.append(conllu)
        json_batch.write_bytes(bytes(json_content))
        conllu_batch.write_text("".join(conllu_content), encoding="utf-8")
        write_json(
            marker,
            {
                "sentence_ids": expected_ids,
                "model_bundle_sha256": model["model_bundle_sha256"],
                "input_sha256": input_sha256,
            },
        )
        completed += len(batch)
        print(f"Annotated {completed}/{len(sources)} sentences.", flush=True)

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("wb") as output:
        for batch_number in range((len(sources) + batch_size - 1) // batch_size):
            output.write((batches_root / f"batch-{batch_number:04d}.jsonl").read_bytes())
    with conllu_path.open("wb") as output:
        for batch_number in range((len(sources) + batch_size - 1) // batch_size):
            output.write((batches_root / f"batch-{batch_number:04d}.conllu").read_bytes())
    runtime = round(time.monotonic() - started, 3)
    report = {
        "sentence_count": len(sources),
        "annotation_jsonl": str(jsonl_path.relative_to(ROOT)),
        "annotation_conllu": str(conllu_path.relative_to(ROOT)),
        "stanza_version": model["stanza_version"],
        "torch_version": model["torch_version"],
        "package": model["package"],
        "processors": list(PROCESSORS),
        "model_bundle_sha256": model["model_bundle_sha256"],
        "model_bytes": model["model_bytes"],
        "gpu_used": gpu_used,
        "hardware": model["hardware"],
        "batch_size": batch_size,
        "runtime_seconds": runtime,
        "completed_at_utc": (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        ),
    }
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-models", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--conllu", type=Path, default=DEFAULT_CONLLU)
    parser.add_argument("--batches", type=Path, default=DEFAULT_BATCHES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    try:
        if args.download_models:
            metadata = download_models()
            print(
                f"Recorded Stanza {metadata['stanza_version']} model metadata in "
                f"{MODEL_REPORT.relative_to(ROOT)}."
            )
            return 0
        if args.batch_size < 1:
            raise ValueError("--batch-size must be positive")
        report = annotate(
            args.input,
            args.jsonl,
            args.conllu,
            args.batches,
            args.report,
            batch_size=args.batch_size,
            use_gpu=not args.cpu,
        )
        print(
            f"Annotated {report['sentence_count']} sentences in "
            f"{report['runtime_seconds']} seconds (GPU: {report['gpu_used']})."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as error:
        print(f"Stanza annotation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
