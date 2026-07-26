#!/usr/bin/env python3
"""Select exactly 10,000 deterministic MASC sentences with provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pipeline_common import (
    DEFAULT_CONFIG,
    DEFAULT_SOURCE_MANIFEST,
    ROOT,
    load_yaml,
    normalized_text,
    read_json,
    read_jsonl,
    sha256_file,
    slug,
    write_json,
    write_jsonl,
)

DEFAULT_INPUT = ROOT / "external" / "audit" / "masc_sentence_candidates.jsonl"
DEFAULT_OANC_INPUT = ROOT / "external" / "audit" / "oanc_sentence_candidates.jsonl"
DEFAULT_OUTPUT = ROOT / "data" / "corpus" / "sentences_10k.jsonl"
DEFAULT_REPORT = ROOT / "reports" / "selection_report.json"
FILTER_VERSION = "1.5.0"

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-])\d{3}[\s.-]\d{4}(?!\d)"
)
FILE_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/(?:home|usr|var|etc)/)\S+")
MARKUP_RE = re.compile(
    r"</?[A-Za-z][^>]*>|(?:^|\s)[{}]{2,}(?:\s|$)|(?:^|\s)//"
)
FORMULA_RE = re.compile(r"(?:[A-Za-z]\s*[=<>]\s*\d|\b(?:http|ftp|mailto):)")
MALFORMED_TEXT_RE = re.compile(
    r"\b(?:aect(?:ed|ing|ive|ively|s)?|aord(?:ed|ing|s)?|"
    r"dicult(?:ies|ly|y)?|dierence|dierent(?:ly)?|"
    r"eect(?:ed|ing|ive|ively|s)?|ecient(?:ly)?|"
    r"oer(?:ed|ing|s)?|sucient(?:ly)?)\b",
    re.IGNORECASE,
)
HEADER_RE = re.compile(
    r"^(?:message-id|date|from|to|subject|mime-version|content-type|"
    r"content-transfer-encoding|posted at|comments?)\s*:",
    re.IGNORECASE,
)
LIST_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[A-Za-z][.)])\s+")
BULLET_LINE_RE = re.compile(r"(?:^|\n)\s*[•·▪◦]\s*")
PRIVATE_DATA_RE = re.compile(
    r"\b(?:social security|ssn|account number|password|confidential question)\b",
    re.IGNORECASE,
)
UNSUITABLE_RE = re.compile(
    r"\b(?:porn(?:ography|ographic)?|rape[ds]?|suicide|behead(?:ed|ing)?|"
    r"lynch(?:ed|ing)?|racial slur|fuck(?:ed|ing|s)?|shit(?:ty|ting)?|"
    r"goddamn|damn(?:ed|it)?|bitch(?:es|y)?|assholes?|bastards?)\b",
    re.IGNORECASE,
)
PUBLIC_TECHNICAL_RE = re.compile(
    r"\b(?:Stanza|Universal Dependencies|UD|(?:re)?mapping|parser|provisional|"
    r"rule-based|manual review|martin-reviewed|auto-high-confidence|"
    r"human-reviewed|needs-review|rejected|nsubj|csubj|iobj|obj|obl|"
    r"ccomp|xcomp|advcl|advmod|nmod|acl|amod)\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
TERMINAL_RE = re.compile(r"[.!?][”’\"')\]]*$")
FINITE_XPOS = {
    "VB", "VBD", "VBP", "VBZ", "MD",
}
SAFE_POS = {
    "PROPN": "Proper noun",
    "NOUN": "Noun",
    "PRON": "Pronoun",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "DET": "Determiner",
    "CCONJ": "Coordinator",
}


def stable_key(seed: int, *parts: object) -> str:
    text = "\0".join([str(seed), *(str(part) for part in parts)])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def balanced_quotes_and_brackets(text: str) -> bool:
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = []
    for character in text:
        if character in pairs:
            stack.append(pairs[character])
        elif character in pairs.values():
            if not stack or stack.pop() != character:
                return False
    if stack:
        return False
    for quote in ('"', "“", "”"):
        if quote == '"' and text.count(quote) % 2:
            return False
    return text.count("“") == text.count("”")


def primary_pos_candidate(record: dict) -> dict | None:
    words = record["words"]
    for word in words:
        label = SAFE_POS.get(word.get("upos"))
        text = word.get("text") or ""
        start, end = word.get("start_char"), word.get("end_char")
        if (
            label
            and isinstance(start, int)
            and isinstance(end, int)
            and end > start
            and text
        ):
            if label == "Proper noun" and not any(character.isupper() for character in text):
                continue
            return {"start": start, "end": end, "label": label}
    for word in words:
        if word.get("upos") not in {"VERB", "AUX"}:
            continue
        start, end = word.get("start_char"), word.get("end_char")
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            continue
        lemma = (word.get("lemma") or "").casefold()
        xpos = word.get("xpos")
        if word["upos"] == "VERB":
            label = "Lexical verb"
        elif xpos == "MD":
            label = "Modal auxiliary"
        elif lemma in {"be", "have", "do"}:
            label = "Auxiliary verb"
        else:
            continue
        return {"start": start, "end": end, "label": label}
    return None


def rejection_reasons(record: dict, *, minimum: int, maximum: int) -> list[str]:
    text = record["text"]
    words = record["words"]
    lexical = [word for word in words if word.get("upos") not in {"PUNCT", "SYM"}]
    reasons = []
    if len(lexical) < minimum:
        reasons.append("too_few_lexical_tokens")
    if len(lexical) > maximum:
        reasons.append("too_many_lexical_tokens")
    if not any(word.get("xpos") in FINITE_XPOS for word in words):
        reasons.append("no_finite_verb")
    if URL_RE.search(text):
        reasons.append("url")
    if EMAIL_RE.search(text):
        reasons.append("email_address")
    if PHONE_RE.search(text):
        reasons.append("phone_number")
    if FILE_PATH_RE.search(text):
        reasons.append("file_path")
    if MARKUP_RE.search(text) or FORMULA_RE.search(text):
        reasons.append("markup_or_formula")
    if MALFORMED_TEXT_RE.search(text):
        reasons.append("source_extraction_artifact")
    if HEADER_RE.search(text) or LIST_RE.search(text) or BULLET_LINE_RE.search(text):
        reasons.append("header_or_list_fragment")
    if "\ufffd" in text or not balanced_quotes_and_brackets(text):
        reasons.append("encoding_or_unmatched_delimiter")
    if PRIVATE_DATA_RE.search(text):
        reasons.append("private_data")
    if UNSUITABLE_RE.search(text):
        reasons.append("unsuitable_content")
    if PUBLIC_TECHNICAL_RE.search(text):
        reasons.append("public_technical_terminology")
    nonspace = [character for character in text if not character.isspace()]
    symbol_count = sum(
        not character.isalpha() and not character.isspace()
        for character in text
    )
    if nonspace and symbol_count / len(nonspace) > 0.20:
        reasons.append("too_many_digits_or_symbols")
    letters = [character for character in text if character.isalpha()]
    if letters and len(letters) >= 8 and all(character.isupper() for character in letters):
        reasons.append("all_caps")
    if re.search(r"[!?.,:;]{4,}", text):
        reasons.append("excessive_punctuation")
    if len(text.strip()) < 20 or not TERMINAL_RE.search(text.strip()):
        reasons.append("fragment_or_missing_terminal_punctuation")
    if primary_pos_candidate(record) is None:
        reasons.append("no_high_confidence_question")
    return sorted(set(reasons))


def complexity(record: dict) -> int:
    words = record["words"]
    lexical = [word for word in words if word.get("upos") not in {"PUNCT", "SYM"}]
    finite = sum(word.get("xpos") in FINITE_XPOS for word in words)
    clause_markers = sum(word.get("upos") == "SCONJ" for word in words)
    nonfinite = sum(word.get("xpos") in {"VBG", "VBN", "TO"} for word in words)
    return len(lexical) + max(0, finite - 1) * 6 + clause_markers * 4 + nonfinite * 2


def sentence_id(record: dict) -> str:
    corpus = record.get("corpus", "MASC").casefold()
    return (
        f"{corpus}-{slug(record['genre'])}-{slug(record['document_id'])}-"
        f"s{int(record['sentence_index']):04d}"
    )


def record_key(record: dict) -> tuple[str, str, int]:
    return (
        record.get("corpus", "MASC"),
        record["source_path"],
        int(record["sentence_index"]),
    )


def document_key(record: dict) -> str:
    return f"{record.get('corpus', 'MASC')}:{record['document_id']}"


def round_robin_documents(
    candidates: list[dict],
    *,
    target: int,
    document_cap: int,
    document_counts: Counter,
    seed: int,
) -> list[dict]:
    by_document = defaultdict(list)
    for record in candidates:
        by_document[document_key(record)].append(record)
    for document, values in by_document.items():
        values.sort(
            key=lambda record: stable_key(
                seed, record["source_path"], record["sentence_index"]
            )
        )
    documents = sorted(
        by_document,
        key=lambda document: stable_key(seed, "document", document),
    )
    selected = []
    cursor = 0
    while documents and len(selected) < target:
        document = documents[cursor % len(documents)]
        values = by_document[document]
        if document_counts[document] >= document_cap or not values:
            documents.remove(document)
            if documents:
                cursor %= len(documents)
            continue
        selected.append(values.pop())
        document_counts[document] += 1
        cursor += 1
    return selected


def assign_difficulty(records: list[dict], config: dict, seed: int) -> None:
    ordered = sorted(
        records,
        key=lambda record: (
            complexity(record),
            stable_key(seed, record["source_path"], record["sentence_index"]),
        ),
    )
    total = len(ordered)
    basic_end = round(total * config["selection"]["difficulty"]["basic"])
    intermediate_end = basic_end + round(
        total * config["selection"]["difficulty"]["intermediate"]
    )
    for index, record in enumerate(ordered):
        if index < basic_end:
            record["_difficulty"] = "basic"
        elif index < intermediate_end:
            record["_difficulty"] = "intermediate"
        else:
            record["_difficulty"] = "advanced"


def deduplicate(records: list[dict], seed: int) -> tuple[list[dict], Counter]:
    kept = []
    seen_exact = set()
    prefix_buckets = defaultdict(list)
    reasons = Counter()
    for record in sorted(
        records,
        key=lambda item: stable_key(
            seed,
            item.get("corpus", "MASC"),
            item["source_path"],
            item["sentence_index"],
        ),
    ):
        normalized = normalized_text(record["text"])
        if normalized in seen_exact:
            reasons["exact_duplicate"] += 1
            continue
        tokens = WORD_RE.findall(normalized)
        signature = " ".join(tokens)
        bucket = (signature[:32], len(tokens) // 3)
        near = False
        for previous in prefix_buckets[bucket]:
            a, b = set(tokens), previous
            similarity = len(a & b) / max(1, len(a | b))
            if similarity >= 0.92:
                near = True
                break
        if near:
            reasons["near_duplicate"] += 1
            continue
        seen_exact.add(normalized)
        prefix_buckets[bucket].append(set(tokens))
        kept.append(record)
    return kept, reasons


def select(config: dict, source_manifest: dict, candidates: list[dict]) -> tuple[list[dict], dict]:
    seed = int(config["seed"])
    target_total = int(config["target_sentences"])
    minimum = int(config["selection"]["lexical_tokens"]["min"])
    maximum = int(config["selection"]["lexical_tokens"]["max"])
    excluded = set(config["selection"]["excluded_genres_initial"])
    source_by_corpus = {
        source["corpus"]: source for source in source_manifest["sources"]
    }
    rejection_counts = Counter()
    rejection_by_genre = defaultdict(Counter)
    rejection_by_source = defaultdict(Counter)
    eligible = []
    for record in candidates:
        record.setdefault("corpus", "MASC")
        if record["genre"] in excluded:
            rejection_counts["excluded_genre"] += 1
            rejection_by_genre[record["genre"]]["excluded_genre"] += 1
            rejection_by_source[record["corpus"]]["excluded_genre"] += 1
            continue
        reasons = rejection_reasons(record, minimum=minimum, maximum=maximum)
        if reasons:
            for reason in reasons:
                rejection_counts[reason] += 1
                rejection_by_genre[record["genre"]][reason] += 1
                rejection_by_source[record["corpus"]][reason] += 1
            continue
        eligible.append(record)
    eligible, duplicate_rejections = deduplicate(eligible, seed)
    rejection_counts.update(duplicate_rejections)
    if len(eligible) < target_total:
        raise ValueError(
            f"MASC/OANC provide only {len(eligible)} eligible unique sentences; "
            f"{target_total - len(eligible)} more are required"
        )

    assign_difficulty(eligible, config, seed)
    masc_eligible = [record for record in eligible if record["corpus"] == "MASC"]
    oanc_eligible = [record for record in eligible if record["corpus"] == "OANC"]
    genre_targets = {
        **config["selection"]["written_genres"],
        **config["selection"]["dialogic_genres"],
    }
    difficulty_targets = {
        name: round(target_total * float(share))
        for name, share in config["selection"]["difficulty"].items()
    }
    difficulty_targets["intermediate"] += target_total - sum(difficulty_targets.values())
    document_cap = min(
        int(config["selection"]["max_sentences_per_document"]),
        math.floor(target_total * float(config["selection"]["max_document_fraction"])),
    )
    selected = []
    selected_keys = set()
    document_counts = Counter()
    requested_cells = {}
    actual_cells = Counter()
    for genre, genre_target in genre_targets.items():
        allocated = {
            difficulty: round(genre_target * float(share))
            for difficulty, share in config["selection"]["difficulty"].items()
        }
        allocated["intermediate"] += genre_target - sum(allocated.values())
        for difficulty, cell_target in allocated.items():
            requested_cells[f"{genre}:{difficulty}"] = cell_target
            pool = [
                record
                for record in masc_eligible
                if record["genre"] == genre
                and record["_difficulty"] == difficulty
                and record_key(record) not in selected_keys
            ]
            chosen = round_robin_documents(
                pool,
                target=cell_target,
                document_cap=document_cap,
                document_counts=document_counts,
                seed=seed,
            )
            for record in chosen:
                key = record_key(record)
                selected_keys.add(key)
                selected.append(record)
                actual_cells[f"{genre}:{difficulty}"] += 1

    remaining_by_difficulty = Counter(difficulty_targets)
    remaining_by_difficulty.subtract(record["_difficulty"] for record in selected)
    for difficulty in ("basic", "intermediate", "advanced"):
        need = max(0, remaining_by_difficulty[difficulty])
        pool = [
            record
            for record in masc_eligible
            if record["_difficulty"] == difficulty
            and record_key(record) not in selected_keys
        ]
        chosen = round_robin_documents(
            pool,
            target=need,
            document_cap=document_cap,
            document_counts=document_counts,
            seed=seed + 1,
        )
        for record in chosen:
            selected_keys.add(record_key(record))
            selected.append(record)

    masc_selected_count = len(selected)
    remaining_by_difficulty = Counter(difficulty_targets)
    remaining_by_difficulty.subtract(record["_difficulty"] for record in selected)
    for difficulty in ("basic", "intermediate", "advanced"):
        need = max(0, remaining_by_difficulty[difficulty])
        pool = [
            record
            for record in oanc_eligible
            if record["_difficulty"] == difficulty
            and record_key(record) not in selected_keys
        ]
        chosen = round_robin_documents(
            pool,
            target=need,
            document_cap=document_cap,
            document_counts=document_counts,
            seed=seed + 2,
        )
        for record in chosen:
            selected_keys.add(record_key(record))
            selected.append(record)
    if len(selected) != target_total:
        fallback_needed = target_total - masc_selected_count
        raise ValueError(
            f"MASC contributes {masc_selected_count} compliant sentences and the "
            f"written OANC input supplies only {len(selected) - masc_selected_count} "
            f"of the {fallback_needed} required fallback sentences"
        )

    selected.sort(key=lambda record: sentence_id(record))
    output = []
    for record in selected:
        registered_source = source_by_corpus[record["corpus"]]
        basis = primary_pos_candidate(record)
        document_start = int(record.get("document_start_char", 0))
        basis = {
            **basis,
            "start": basis["start"] - document_start,
            "end": basis["end"] - document_start,
        }
        if not 0 <= basis["start"] < basis["end"] <= len(record["text"]):
            raise ValueError(
                f"{record['source_path']} sentence {record['sentence_index']}: "
                "primary candidate offsets do not align with selected text"
            )
        output.append(
            {
                "sentence_id": sentence_id(record),
                "text": record["text"],
                "language": "en",
                "variety": "en-US",
                "source": {
                    "corpus": record["corpus"],
                    "corpus_version": registered_source["version"],
                    "document_id": record["document_id"],
                    "genre": record["genre"],
                    "source_path": record["source_path"],
                    "licence": registered_source["licence"],
                    "attribution": registered_source["attribution"],
                    "sentence_index": record["sentence_index"],
                    **(
                        {"collection": record["collection"]}
                        if record.get("collection")
                        else {}
                    ),
                    **(
                        {"domain": record["domain"]}
                        if record.get("domain")
                        else {}
                    ),
                },
                "selection": {
                    "seed": seed,
                    "difficulty": record["_difficulty"],
                    "filter_version": FILTER_VERSION,
                    "lexical_tokens": sum(
                        word.get("upos") not in {"PUNCT", "SYM"}
                        for word in record["words"]
                    ),
                    "finite_verbs": sum(
                        word.get("xpos") in FINITE_XPOS for word in record["words"]
                    ),
                    "complexity_score": complexity(record),
                    "primary_pos_candidate": basis,
                },
            }
        )
    source_counts = Counter(item["source"]["corpus"] for item in output)
    genre_counts = Counter(item["source"]["genre"] for item in output)
    difficulty_counts = Counter(item["selection"]["difficulty"] for item in output)
    normalized = [normalized_text(item["text"]) for item in output]
    report = {
        "selection_seed": seed,
        "filter_version": FILTER_VERSION,
        "target_sentence_count": target_total,
        "accepted_sentence_count": len(output),
        "unique_sentence_id_count": len({item["sentence_id"] for item in output}),
        "unique_normalized_text_count": len(set(normalized)),
        "eligible_masc_sentence_count": len(masc_eligible),
        "eligible_oanc_sentence_count": len(oanc_eligible),
        "oanc_fallback_needed": source_counts["OANC"] > 0,
        "oanc_fallback_sentence_count": source_counts["OANC"],
        "document_cap": document_cap,
        "maximum_document_contribution": max(document_counts.values()),
        "rejections_by_reason": dict(sorted(rejection_counts.items())),
        "rejections_by_genre": {
            genre: dict(sorted(values.items()))
            for genre, values in sorted(rejection_by_genre.items())
        },
        "rejections_by_source": {
            corpus: dict(sorted(values.items()))
            for corpus, values in sorted(rejection_by_source.items())
        },
        "accepted_by_source": dict(sorted(source_counts.items())),
        "accepted_by_genre": dict(sorted(genre_counts.items())),
        "accepted_by_difficulty": dict(sorted(difficulty_counts.items())),
        "soft_genre_difficulty_targets": requested_cells,
        "soft_genre_difficulty_actual": dict(sorted(actual_cells.items())),
        "redistribution_by_genre": {
            genre: genre_counts[genre] - int(target)
            for genre, target in genre_targets.items()
        },
        "source_archive_sha256": {
            source["corpus"]: source["archive_sha256"]
            for source in source_manifest["sources"]
            if source.get("archive_sha256")
        },
    }
    return output, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--oanc-input", type=Path, default=DEFAULT_OANC_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        manifest = read_json(args.manifest)
        candidates = list(read_jsonl(args.input))
        if args.oanc_input.exists():
            candidates.extend(read_jsonl(args.oanc_input))
        records, report = select(load_yaml(args.config), manifest, candidates)
        write_jsonl(args.output, records)
        report["selected_jsonl_sha256"] = sha256_file(args.output)
        write_json(args.report, report)
        for source in manifest["sources"]:
            source["used_sentence_count"] = report["accepted_by_source"].get(
                source["corpus"], 0
            )
        write_json(args.manifest, manifest)
        print(
            f"Selected {len(records)} sentences to {args.output.relative_to(ROOT)}.\n"
            f"- genres: {report['accepted_by_genre']}\n"
            f"- difficulty: {report['accepted_by_difficulty']}\n"
            f"- OANC fallback needed: {report['oanc_fallback_needed']}"
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Sentence selection failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
