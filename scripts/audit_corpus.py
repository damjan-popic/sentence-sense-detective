#!/usr/bin/env python3
"""Audit and pre-annotate MASC documents for deterministic sentence selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from pipeline_common import (
    ROOT,
    canonical_json_bytes,
    load_yaml,
    sha256_file,
    slug,
    write_json,
)
from stanza_support import ensure_models, load_pipeline, word_record

DEFAULT_INPUT = ROOT / "external" / "masc-3.0.0" / "masc_500k_texts"
DEFAULT_OUTPUT = ROOT / "external" / "audit" / "masc_sentence_candidates.jsonl"
DEFAULT_REPORT = ROOT / "reports" / "corpus_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "corpus_audit.md"

GENRE_MAP = {
    "blog": "blog",
    "email": "email",
    "essays": "essay",
    "fiction": "fiction",
    "ficlets": "ficlets",
    "govt-docs": "government",
    "journal": "journal",
    "letters": "letters",
    "newspaper:newswire": "newspaper",
    "non-fiction": "nonfiction",
    "technical": "technical",
    "travel-guides": "travel",
    "court transcript": "court",
    "debate-transcript": "debate",
    "face-to-face": "spoken",
    "telephone": "spoken",
    "movie-script": "movie-script",
    "spam": "spam",
    "twitter": "twitter",
    "jokes": "jokes",
}


def document_metadata(root: Path, path: Path, corpus: str) -> dict:
    relative = path.relative_to(root)
    if corpus == "OANC":
        if len(relative.parts) < 4 or not relative.parts[0].startswith("written_"):
            raise ValueError(f"unexpected written OANC path: {relative}")
        broad_genre, collection = relative.parts[1], relative.parts[2]
        if broad_genre == "technical" and collection in {"government", "911report"}:
            genre = "government"
        else:
            genre = {
                "journal": "journal",
                "letters": "letters",
                "fiction": "fiction",
                "technical": "technical",
                "travel_guides": "travel",
                "non-fiction": "nonfiction",
            }.get(broad_genre)
        if genre is None:
            raise ValueError(f"unmapped written OANC genre {broad_genre!r}")
        return {
            "stratum": "written",
            "source_genre": broad_genre,
            "genre": genre,
            "source_path": relative.as_posix(),
            "document_id": f"{collection}-{slug(path.stem)}",
            "collection": collection,
            "domain": broad_genre,
        }
    if len(relative.parts) < 3:
        raise ValueError(f"unexpected MASC path: {relative}")
    stratum, source_genre = relative.parts[0], relative.parts[1]
    genre = GENRE_MAP.get(source_genre)
    if genre is None:
        raise ValueError(f"unmapped MASC genre {source_genre!r}")
    return {
        "stratum": stratum,
        "source_genre": source_genre,
        "genre": genre,
        "source_path": relative.as_posix(),
        "document_id": f"{genre}-{slug(path.stem)}",
    }


def valid_sentence_span(sentence, document_text: str) -> tuple[int, int] | None:
    starts = [
        word.start_char
        for word in sentence.words
        if word.start_char is not None
    ]
    ends = [
        word.end_char
        for word in sentence.words
        if word.end_char is not None
    ]
    if not starts or not ends:
        return None
    start, end = min(starts), max(ends)
    if start < 0 or end <= start or end > len(document_text):
        return None
    return int(start), int(end)


def audit(
    input_root: Path,
    output: Path,
    *,
    use_gpu: bool,
    corpus: str = "MASC",
    max_documents: int | None = None,
    report_path: Path | None = None,
) -> dict:
    model = ensure_models()
    documents = sorted(input_root.rglob("*.txt"))
    available_document_count = len(documents)
    if max_documents is not None:
        documents.sort(
            key=lambda path: hashlib.sha256(
                f"20260726\0{path.relative_to(input_root).as_posix()}".encode("utf-8")
            ).hexdigest()
        )
        documents = documents[:max_documents]
    input_digest = hashlib.sha256()
    for path in documents:
        input_digest.update(path.relative_to(input_root).as_posix().encode("utf-8"))
        input_digest.update(b"\0")
        input_digest.update(sha256_file(path).encode("ascii"))
    input_fingerprint = input_digest.hexdigest()
    if output.exists() and report_path and report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        matching = (
            existing.get("corpus") == corpus
            and existing.get("document_count") == len(documents)
            and existing.get("available_document_count") == available_document_count
            and existing.get("stanza", {}).get("model_bundle_sha256")
            == model["model_bundle_sha256"]
            and existing.get("input_fingerprint_sha256") in {None, input_fingerprint}
        )
        if matching:
            existing["input_fingerprint_sha256"] = input_fingerprint
            existing["candidate_file_sha256"] = sha256_file(output)
            print(
                f"Using existing verified {corpus} audit "
                f"{output.resolve().relative_to(ROOT)}."
            )
            return existing
    nlp, gpu_used = load_pipeline(("tokenize", "mwt", "pos", "lemma"), use_gpu=use_gpu)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    counts = Counter()
    genre_documents = Counter()
    genre_sentences = Counter()
    genre_tokens = Counter()
    failures = []
    started = time.monotonic()
    try:
        with temporary.open("wb") as handle:
            for document_number, path in enumerate(documents, 1):
                metadata = document_metadata(input_root, path, corpus)
                genre_documents[metadata["genre"]] += 1
                text = path.read_text(encoding="utf-8-sig", errors="strict")
                counts["raw_characters"] += len(text)
                try:
                    annotated = nlp(text)
                except Exception as error:  # pragma: no cover - external model failure
                    failures.append(
                        {
                            "source_path": metadata["source_path"],
                            "error": f"{type(error).__name__}: {error}",
                        }
                    )
                    continue
                for sentence_index, sentence in enumerate(annotated.sentences, 1):
                    span = valid_sentence_span(sentence, text)
                    if span is None:
                        counts["invalid_sentence_offsets"] += 1
                        continue
                    start, end = span
                    sentence_text = text[start:end]
                    words = [word_record(word) for word in sentence.words]
                    record = {
                        "corpus": corpus,
                        "corpus_version": (
                            "3.0.0" if corpus == "MASC" else "GrAF release 2011-07-16"
                        ),
                        "licence": (
                            "CC BY 3.0 US"
                            if corpus == "MASC"
                            else "Unrestricted use and redistribution (Open ANC terms)"
                        ),
                        "attribution": (
                            "Open American National Corpus / MASC"
                            if corpus == "MASC"
                            else "Open American National Corpus"
                        ),
                        "document_id": metadata["document_id"],
                        "source_path": metadata["source_path"],
                        "stratum": metadata["stratum"],
                        "source_genre": metadata["source_genre"],
                        "genre": metadata["genre"],
                        "sentence_index": sentence_index,
                        "document_start_char": start,
                        "document_end_char": end,
                        "text": sentence_text,
                        "words": words,
                        **(
                            {"collection": metadata["collection"]}
                            if metadata.get("collection")
                            else {}
                        ),
                        **(
                            {"domain": metadata["domain"]}
                            if metadata.get("domain")
                            else {}
                        ),
                    }
                    handle.write(canonical_json_bytes(record))
                    counts["raw_sentences"] += 1
                    counts["raw_tokens"] += len(words)
                    genre_sentences[metadata["genre"]] += 1
                    genre_tokens[metadata["genre"]] += len(words)
                if document_number % 25 == 0 or document_number == len(documents):
                    print(
                        f"Audited {document_number}/{len(documents)} documents; "
                        f"{counts['raw_sentences']} sentences.",
                        flush=True,
                    )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    report = {
        "corpus": corpus,
        "corpus_version": (
            "3.0.0" if corpus == "MASC" else "GrAF release 2011-07-16"
        ),
        "input_root": str(input_root.resolve().relative_to(ROOT)),
        "candidate_file": str(output.resolve().relative_to(ROOT)),
        "document_count": len(documents),
        "available_document_count": available_document_count,
        "document_failures": failures,
        "raw_sentence_count": counts["raw_sentences"],
        "raw_token_count": counts["raw_tokens"],
        "raw_character_count": counts["raw_characters"],
        "invalid_sentence_offset_count": counts["invalid_sentence_offsets"],
        "input_fingerprint_sha256": input_fingerprint,
        "candidate_file_sha256": sha256_file(output),
        "by_genre": {
            genre: {
                "documents": genre_documents[genre],
                "sentences": genre_sentences[genre],
                "tokens": genre_tokens[genre],
            }
            for genre in sorted(genre_documents)
        },
        "stanza": {
            "version": model["stanza_version"],
            "package": model["package"],
            "model_bundle_sha256": model["model_bundle_sha256"],
            "processors": ["tokenize", "mwt", "pos", "lemma"],
            "gpu_used": gpu_used,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
    }
    return report


def markdown_report(report: dict) -> str:
    lines = [
        f"# {report['corpus']} corpus audit",
        "",
        f"- Documents: {report['document_count']}",
        f"- Raw sentences: {report['raw_sentence_count']}",
        f"- Raw tokens: {report['raw_token_count']}",
        f"- Document failures: {len(report['document_failures'])}",
        f"- Runtime: {report['runtime_seconds']} seconds",
        "",
        "| Genre | Documents | Sentences | Tokens |",
        "|---|---:|---:|---:|",
    ]
    for genre, values in report["by_genre"].items():
        lines.append(
            f"| {genre} | {values['documents']} | {values['sentences']} | {values['tokens']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--corpus", choices=("MASC", "OANC"), default="MASC")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--max-documents", type=int)
    args = parser.parse_args()
    try:
        if args.max_documents is not None and args.max_documents < 1:
            raise ValueError("--max-documents must be positive")
        report = audit(
            args.input,
            args.output,
            use_gpu=not args.cpu,
            corpus=args.corpus,
            max_documents=args.max_documents,
            report_path=args.report,
        )
        write_json(args.report, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_report(report), encoding="utf-8")
        print(
            f"Wrote {args.output.resolve().relative_to(ROOT)} and "
            f"{args.report.resolve().relative_to(ROOT)}."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as error:
        print(f"Corpus audit failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
