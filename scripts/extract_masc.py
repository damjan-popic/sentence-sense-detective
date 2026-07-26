#!/usr/bin/env python3
"""Safely extract the immutable MASC data-only archive."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from pipeline_common import ROOT, sha256_file, write_json

DEFAULT_ARCHIVE = ROOT / "external" / "downloads" / "masc_500k_texts.zip"
DEFAULT_OUTPUT = ROOT / "external" / "masc-3.0.0"


def safe_member(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member: {name!r}")
    return path


def extract(archive: Path, output: Path) -> dict:
    if output.exists():
        marker = output / ".extraction.json"
        if marker.exists():
            state = json.loads(marker.read_text(encoding="utf-8"))
            if state.get("archive_sha256") == sha256_file(archive):
                print(f"Using existing verified extraction {output.relative_to(ROOT)}.")
                return state
        raise ValueError(
            f"{output} already exists without a matching extraction marker; "
            "move it aside explicitly before extracting"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=".masc-3.0.0-", dir=output.parent)
    )
    file_count = 0
    total_bytes = 0
    try:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                relative = safe_member(info.filename)
                if not relative.parts:
                    continue
                destination = temporary.joinpath(*relative.parts)
                resolved = destination.resolve()
                if temporary.resolve() not in resolved.parents and resolved != temporary.resolve():
                    raise ValueError(f"archive member escapes extraction root: {info.filename!r}")
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                mode = info.external_attr >> 16
                if mode and (mode & 0o170000) == 0o120000:
                    raise ValueError(f"symbolic links are not accepted: {info.filename!r}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                file_count += 1
                total_bytes += info.file_size
        state = {
            "archive": archive.name,
            "archive_sha256": sha256_file(archive),
            "file_count": file_count,
            "uncompressed_bytes": total_bytes,
        }
        write_json(temporary / ".extraction.json", state)
        os.replace(temporary, output)
        print(
            f"Extracted {file_count} files ({total_bytes} bytes) to "
            f"{output.relative_to(ROOT)}."
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
        print(f"MASC extraction failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
