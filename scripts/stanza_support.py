#!/usr/bin/env python3
"""Pinned Stanza model management and serialisation helpers."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from pipeline_common import ROOT, write_json

LANGUAGE = "en"
PACKAGE = "combined"
PROCESSORS = ("tokenize", "mwt", "pos", "lemma", "depparse")
STANZA_DIR = Path(
    os.environ.get("STANZA_RESOURCES_DIR", str(Path.home() / "stanza_resources"))
).expanduser()
MODEL_REPORT = ROOT / "reports" / "stanza_model.json"


def import_stanza():
    try:
        import stanza
        import torch
    except ImportError as error:  # pragma: no cover - CLI dependency error
        raise RuntimeError(
            "Stanza is required. Create .venv and install requirements-corpus.txt."
        ) from error
    return stanza, torch


def combined_model_hash(directory: Path) -> tuple[str, list[dict]]:
    digest = hashlib.sha256()
    files = []
    for path in sorted((directory / LANGUAGE).rglob("*")):
        if not path.is_file():
            continue
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(directory).as_posix()
        size = path.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        files.append({"path": relative, "bytes": size, "sha256": file_hash})
    return digest.hexdigest(), files


def resource_metadata() -> dict:
    stanza, torch = import_stanza()
    resources_path = STANZA_DIR / "resources.json"
    resources = (
        json.loads(resources_path.read_text(encoding="utf-8"))
        if resources_path.exists()
        else {}
    )
    model_hash, files = combined_model_hash(STANZA_DIR)
    cuda_available = bool(torch.cuda.is_available())
    return {
        "language": LANGUAGE,
        "package": PACKAGE,
        "processors": list(PROCESSORS),
        "stanza_version": stanza.__version__,
        "torch_version": torch.__version__,
        "resources_version": resources.get("resources_version"),
        "model_directory": str(STANZA_DIR),
        "model_file_count": len(files),
        "model_bytes": sum(item["bytes"] for item in files),
        "model_bundle_sha256": model_hash,
        "model_files": files,
        "hardware": {
            "platform": platform.platform(),
            "cuda_available": cuda_available,
            "cuda_device": (
                torch.cuda.get_device_name(0) if cuda_available else None
            ),
        },
    }


def download_models() -> dict:
    stanza, _ = import_stanza()
    STANZA_DIR.mkdir(parents=True, exist_ok=True)
    stanza.download(
        LANGUAGE,
        package=PACKAGE,
        processors=",".join(PROCESSORS),
        model_dir=str(STANZA_DIR),
        verbose=True,
    )
    metadata = resource_metadata()
    metadata["download_checked_at_utc"] = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    write_json(MODEL_REPORT, metadata)
    return metadata


def ensure_models() -> dict:
    if not (STANZA_DIR / LANGUAGE).exists():
        raise RuntimeError(
            f"English Stanza resources are missing from {STANZA_DIR}; "
            "run: make corpus-models"
        )
    metadata = resource_metadata()
    if MODEL_REPORT.exists():
        recorded = json.loads(MODEL_REPORT.read_text(encoding="utf-8"))
        metadata["download_checked_at_utc"] = recorded.get(
            "download_checked_at_utc"
        )
    return metadata


def load_pipeline(
    processors: tuple[str, ...],
    *,
    use_gpu: bool,
    no_sentence_split: bool = False,
):
    stanza, torch = import_stanza()
    gpu = bool(use_gpu and torch.cuda.is_available())
    pipeline = stanza.Pipeline(
        LANGUAGE,
        package=PACKAGE,
        processors=",".join(processors),
        model_dir=str(STANZA_DIR),
        use_gpu=gpu,
        download_method=None,
        tokenize_no_ssplit=no_sentence_split,
        verbose=False,
    )
    return pipeline, gpu


def word_record(word) -> dict:
    return {
        "id": int(word.id),
        "text": word.text,
        "lemma": word.lemma,
        "upos": word.upos,
        "xpos": word.xpos,
        "feats": word.feats,
        "head": int(word.head) if word.head is not None else None,
        "deprel": word.deprel,
        "start_char": int(word.start_char) if word.start_char is not None else None,
        "end_char": int(word.end_char) if word.end_char is not None else None,
    }
