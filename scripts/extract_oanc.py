#!/usr/bin/env python3
"""Safely extract a deterministic written-only OANC audit subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from pipeline_common import ROOT, SEED, sha256_file, write_json

DEFAULT_ARCHIVE = ROOT / "external" / "downloads" / "OANC_GrAF.zip"
DEFAULT_OUTPUT = ROOT / "external" / "oanc"
PER_COLLECTION_LIMIT = 80


def safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member: {name!r}")
    return path


def collection_for(path: PurePosixPath) -> str:
    parts = path.parts
    written_index = next(
        (index for index, part in enumerate(parts) if part.startswith("written_")),
        None,
    )
    if written_index is None or len(parts) <= written_index + 2:
        raise ValueError(f"unexpected written OANC path: {path}")
    return parts[written_index + 2]


def stable_key(name: str) -> str:
    return hashlib.sha256(f"{SEED}\0{name}".encode("utf-8")).hexdigest()


def selected_members(bundle: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], dict]:
    written = []
    by_collection = defaultdict(list)
    for info in bundle.infolist():
        path = safe_member(info.filename)
        if info.is_dir() or path.suffix.casefold() != ".txt":
            continue
        if not any(part.startswith("written_") for part in path.parts):
            continue
        written.append(info)
        by_collection[collection_for(path)].append(info)
    selected = []
    for collection, members in sorted(by_collection.items()):
        members.sort(key=lambda info: stable_key(info.filename))
        selected.extend(members[:PER_COLLECTION_LIMIT])
    selected.sort(key=lambda info: info.filename)
    return selected, {
        "archive_written_text_count": len(written),
        "archive_written_text_bytes": sum(info.file_size for info in written),
        "archive_written_by_collection": dict(
            sorted(Counter(collection_for(safe_member(info.filename)) for info in written).items())
        ),
        "extracted_by_collection": dict(
            sorted(Counter(collection_for(safe_member(info.filename)) for info in selected).items())
        ),
    }


def relative_written_path(path: PurePosixPath) -> Path:
    parts = path.parts
    data_index = parts.index("data")
    return Path(*parts[data_index + 1 :])


def extract(archive: Path, output: Path) -> dict:
    archive_hash = sha256_file(archive)
    marker = output / ".extraction.json"
    if output.exists():
        if marker.exists():
            state = json.loads(marker.read_text(encoding="utf-8"))
            if state.get("archive_sha256") == archive_hash:
                print(f"Using existing verified OANC extraction {output.relative_to(ROOT)}.")
                return state
        raise ValueError(
            f"{output} already exists without a matching extraction marker; "
            "move it aside explicitly before extracting"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".oanc-", dir=output.parent))
    try:
        with zipfile.ZipFile(archive) as bundle:
            members, inventory = selected_members(bundle)
            for info in members:
                path = safe_member(info.filename)
                destination = temporary / relative_written_path(path)
                resolved = destination.resolve()
                if temporary.resolve() not in resolved.parents:
                    raise ValueError(f"archive member escapes extraction root: {info.filename!r}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
        state = {
            "archive": archive.name,
            "archive_sha256": archive_hash,
            "selection_seed": SEED,
            "per_collection_limit": PER_COLLECTION_LIMIT,
            "extracted_text_count": len(members),
            "extracted_text_bytes": sum(info.file_size for info in members),
            **inventory,
        }
        write_json(temporary / ".extraction.json", state)
        os.replace(temporary, output)
        print(
            f"Extracted {len(members)} deterministic written OANC documents "
            f"({state['extracted_text_bytes']} bytes) to {output.relative_to(ROOT)}."
        )
        return state
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        extract(args.archive, args.output)
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(f"OANC extraction failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
