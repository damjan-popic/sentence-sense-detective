#!/usr/bin/env python3
"""Deterministically import explicit decisions from the generated review workbook."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

from pipeline_common import ROOT, read_json, read_jsonl, sha256_file, write_json, write_jsonl

DEFAULT_WORKBOOK = ROOT / "data" / "review" / "review_pack.xlsx"
DEFAULT_CANDIDATES = (
    ROOT / "data" / "generated" / "question_candidates.jsonl.gz"
)
DEFAULT_TAGSET = ROOT / "config" / "pedagogical_tagset_en.json"
DEFAULT_OUTPUT = ROOT / "data" / "review" / "corrections"
DECISIONS = {"accept", "correct", "reject"}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CELL_RE = re.compile(r"([A-Z]+)(\d+)")


def column_index(reference: str) -> int:
    match = CELL_RE.fullmatch(reference)
    if not match:
        raise ValueError(f"invalid workbook cell reference {reference!r}")
    value = 0
    for character in match.group(1):
        value = value * 26 + ord(character) - 64
    return value - 1


def shared_strings(bundle: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in bundle.namelist():
        return []
    root = ET.fromstring(bundle.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall("m:si", NS):
        values.append("".join(node.text or "" for node in item.findall(".//m:t", NS)))
    return values


def cell_value(cell, strings: list[str]):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//m:t", NS))
    value_node = cell.find("m:v", NS)
    if value_node is None:
        return ""
    value = value_node.text or ""
    if cell_type == "s":
        return strings[int(value)]
    if cell_type in {"str", "d"}:
        return value
    if cell_type == "b":
        return value == "1"
    try:
        return float(value)
    except ValueError:
        return value


def read_review_sheets(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as bundle:
        strings = shared_strings(bundle)
        sheet_names = sorted(
            (
                name
                for name in bundle.namelist()
                if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
            ),
            key=lambda name: int(re.search(r"\d+", name).group()),
        )
        result = []
        expected_headers = None
        for sheet_name in sheet_names:
            root = ET.fromstring(bundle.read(sheet_name))
            rows = []
            for row in root.findall(".//m:sheetData/m:row", NS):
                values = {}
                for cell in row.findall("m:c", NS):
                    values[column_index(cell.attrib["r"])] = cell_value(
                        cell, strings
                    )
                if values:
                    rows.append(
                        [
                            values.get(index, "")
                            for index in range(max(values) + 1)
                        ]
                    )
            if not rows:
                continue
            headers = [str(value).strip() for value in rows[0]]
            if expected_headers is None:
                expected_headers = headers
            elif headers != expected_headers:
                raise ValueError(
                    f"{sheet_name}: review headers differ from the first sheet"
                )
            for values in rows[1:]:
                values += [""] * (len(headers) - len(values))
                result.append(dict(zip(headers, values, strict=True)))
    if not result:
        raise ValueError("review workbook contains no candidate rows")
    return result


def review_date(value) -> str:
    if value in ("", None):
        return ""
    if isinstance(value, (int, float)):
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError as error:
        raise ValueError(f"invalid review date {text!r}; use YYYY-MM-DD") from error


def parse_target(value, sentence: str, current: list[dict]) -> list[dict]:
    text = str(value or "").strip()
    if not text:
        return current
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        spans = parsed
    elif re.fullmatch(r"\d+:\d+(?:\s*,\s*\d+:\d+)*", text):
        spans = [
            {"start": int(start), "end": int(end)}
            for start, end in (
                part.strip().split(":", 1) for part in text.split(",")
            )
        ]
    else:
        positions = [
            match.start()
            for match in re.finditer(re.escape(text), sentence)
        ]
        if len(positions) != 1:
            raise ValueError(
                f"corrected target {text!r} must occur exactly once or use start:end offsets"
            )
        spans = [{"start": positions[0], "end": positions[0] + len(text)}]
    for span in spans:
        if (
            set(span) != {"start", "end"}
            or not isinstance(span["start"], int)
            or not isinstance(span["end"], int)
            or not 0 <= span["start"] < span["end"] <= len(sentence)
        ):
            raise ValueError(f"invalid corrected target span {span!r}")
    return spans


def apply_reviews(
    candidates: list[dict],
    rows: list[dict],
    tagset: dict,
    source_file: Path,
) -> tuple[list[dict], list[dict], dict]:
    by_id = {candidate["question_id"]: copy.deepcopy(candidate) for candidate in candidates}
    reviewed_ids = set()
    changes = []
    for row_number, row in enumerate(rows, 2):
        decision = str(row.get("accept / correct / reject", "") or "").strip().casefold()
        if not decision:
            continue
        if decision not in DECISIONS:
            raise ValueError(f"row {row_number}: invalid decision {decision!r}")
        question_id = str(row.get("question ID", "") or "").strip()
        if question_id in reviewed_ids:
            raise ValueError(f"row {row_number}: duplicate review for {question_id}")
        reviewed_ids.add(question_id)
        if question_id not in by_id:
            raise ValueError(f"row {row_number}: unknown question ID {question_id!r}")
        candidate = by_id[question_id]
        reviewer = str(row.get("reviewer", "") or "").strip()
        date = review_date(row.get("review date"))
        if not reviewer or not date:
            raise ValueError(
                f"row {row_number}: reviewer and review date are required for a decision"
            )
        before = copy.deepcopy(candidate)
        if decision == "reject":
            candidate["review_status"] = "rejected"
        else:
            candidate["review_status"] = "human-reviewed"
        if decision == "correct":
            candidate["target_spans"] = parse_target(
                row.get("corrected target"),
                candidate["sentence"],
                candidate["target_spans"],
            )
            corrected_answer = str(row.get("corrected answer", "") or "").strip()
            if corrected_answer:
                dimension_labels = tagset["dimensions"][candidate["dimension"]]["labels"]
                if corrected_answer not in dimension_labels:
                    raise ValueError(
                        f"row {row_number}: corrected answer is outside the controlled vocabulary"
                    )
                if corrected_answer not in candidate["options"]:
                    candidate["options"] = [
                        corrected_answer,
                        *[
                            option
                            for option in candidate["options"]
                            if option != candidate["answer"]
                        ][:3],
                    ]
                candidate["answer"] = corrected_answer
            corrected_explanation = str(
                row.get("corrected explanation", "") or ""
            ).strip()
            if corrected_explanation:
                candidate["explanation"] = corrected_explanation
        if len(candidate["options"]) != 4 or len(set(candidate["options"])) != 4:
            raise ValueError(f"row {row_number}: correction does not leave four unique options")
        if candidate["answer"] not in candidate["options"]:
            raise ValueError(f"row {row_number}: correction omits the answer from options")
        changes.append(
            {
                "question_id": question_id,
                "decision": decision,
                "reviewer": reviewer,
                "review_date": date,
                "note": str(row.get("note", "") or "").strip(),
                "before": before,
                "after": copy.deepcopy(candidate),
            }
        )
    updated = sorted(by_id.values(), key=lambda item: item["question_id"])
    accepted = [
        candidate
        for candidate in updated
        if candidate["review_status"] in {"auto-high-confidence", "human-reviewed"}
    ]
    change_log = {
        "source_file": str(source_file),
        "source_sha256": sha256_file(source_file),
        "decision_count": len(changes),
        "changes": changes,
    }
    return updated, accepted, change_log


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--tagset", type=Path, default=DEFAULT_TAGSET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="replace generated candidate/accepted files after a validated import",
    )
    args = parser.parse_args()
    try:
        digest = sha256_file(args.workbook)
        updated, accepted, log = apply_reviews(
            list(read_jsonl(args.candidates)),
            read_review_sheets(args.workbook),
            read_json(args.tagset),
            args.workbook,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"review-{digest[:12]}"
        write_jsonl(args.output_dir / f"{stem}-candidates.jsonl", updated)
        write_jsonl(args.output_dir / f"{stem}-accepted.jsonl", accepted)
        write_json(args.output_dir / f"{stem}-changes.json", log)
        if args.apply:
            write_jsonl(DEFAULT_CANDIDATES, updated)
            write_jsonl(
                ROOT / "data" / "generated" / "accepted_questions.jsonl.gz",
                accepted,
            )
        print(
            f"Imported {log['decision_count']} review decisions; "
            f"apply to generated data: {args.apply}."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"Review import failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
