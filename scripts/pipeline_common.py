#!/usr/bin/env python3
"""Shared deterministic helpers for the local corpus build."""

from __future__ import annotations

import hashlib
import gzip
import io
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "corpus_10k.yaml"
DEFAULT_SOURCE_MANIFEST = ROOT / "config" / "source_manifest.json"
SEED = 20260726


def load_yaml(path: Path = DEFAULT_CONFIG) -> dict:
    try:
        import yaml
    except ImportError as error:  # pragma: no cover - exercised by CLI error path
        raise RuntimeError(
            "PyYAML is required. Create .venv and install requirements-corpus.txt."
        ) from error
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML object")
    return value


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    values = []
    if path.suffix == ".gz":
        handle_context = gzip.open(path, mode="rt", encoding="utf-8")
    else:
        handle_context = path.open(encoding="utf-8")
    with handle_context as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            values.append(value)
    return values


def canonical_json_bytes(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        text = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ) + "\n"
    return text.encode("utf-8")


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, value: object, *, pretty: bool = True) -> None:
    atomic_write(path, canonical_json_bytes(value, pretty=pretty))


def write_jsonl(path: Path, values: Iterable[dict]) -> None:
    content = b"".join(canonical_json_bytes(value) for value in values)
    if path.suffix == ".gz":
        compressed = io.BytesIO()
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=compressed,
            mtime=0,
        ) as handle:
            handle.write(content)
        content = compressed.getvalue()
    atomic_write(path, content)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def slug(value: str, *, limit: int = 72) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (cleaned[:limit].rstrip("-") or "document")


def codepoint_slice(text: str, start: int, end: int) -> str:
    """Python indexes strings by Unicode code point, matching the public contract."""
    return text[start:end]
