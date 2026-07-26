#!/usr/bin/env python3
"""Fetch immutable official MASC/OANC archives and record provenance."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pipeline_common import (
    DEFAULT_CONFIG,
    DEFAULT_SOURCE_MANIFEST,
    ROOT,
    load_yaml,
    read_json,
    sha256_file,
    write_json,
)

ALLOWED_HOSTS = {"anc.org", "www.anc.org"}


def open_official(url: str, *, allow_insecure_tls: bool):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"refusing non-official corpus URL: {url}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SentenceSenseDetectiveCorpusBuilder/1.0"},
    )
    try:
        return urllib.request.urlopen(request, timeout=60), True
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", None)
        certificate_error = isinstance(reason, ssl.SSLCertVerificationError)
        if not (allow_insecure_tls and certificate_error):
            raise
        print(
            "WARNING: the official ANC certificate did not validate; retrying the exact "
            "allowlisted anc.org URL without certificate verification.",
            file=sys.stderr,
        )
        context = ssl._create_unverified_context()  # noqa: SLF001 - explicit CLI opt-in
        return urllib.request.urlopen(request, timeout=60, context=context), False


def download(
    *,
    url: str,
    destination: Path,
    allow_insecure_tls: bool,
) -> tuple[str, int, bool]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        response, tls_verified = open_official(
            url, allow_insecure_tls=allow_insecure_tls
        )
        resolved_url = response.geturl()
        resolved_host = urllib.parse.urlparse(resolved_url).hostname
        if resolved_host not in ALLOWED_HOSTS:
            raise ValueError(f"official download redirected outside anc.org: {resolved_url}")
        with response, temporary.open("wb") as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return resolved_url, destination.stat().st_size, tls_verified


def update_manifest(
    manifest_path: Path,
    *,
    official_page: str,
    resolved_url: str,
    archive: Path,
    tls_verified: bool,
    retrieved_at: str,
    corpus: str,
) -> dict:
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"{manifest_path}: expected an object")
    source = next(item for item in manifest["sources"] if item.get("corpus") == corpus)
    source.update(
        {
            "official_page": official_page,
            "resolved_download_url": resolved_url,
            "retrieved_at_utc": retrieved_at,
            "archive_filename": archive.name,
            "archive_bytes": archive.stat().st_size,
            "archive_sha256": sha256_file(archive),
            "tls_certificate_verified": tls_verified,
        }
    )
    write_json(manifest_path, manifest)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--source", choices=("masc", "oanc"), default="masc")
    parser.add_argument(
        "--allow-insecure-tls",
        action="store_true",
        help="permit the exact official ANC URL when its certificate has expired",
    )
    args = parser.parse_args()
    try:
        config = load_yaml(args.config)
        source_config = config["sources"][
            "primary" if args.source == "masc" else "fallback"
        ]
        corpus = source_config["corpus"]
        destination = ROOT / "external" / "downloads" / source_config["archive_filename"]
        existing = None
        if args.manifest.exists():
            current = read_json(args.manifest)
            existing = next(
                (
                    source
                    for source in current.get("sources", [])
                    if source.get("corpus") == corpus
                ),
                None,
            )
        if destination.exists():
            digest = sha256_file(destination)
            if existing and existing.get("archive_sha256") == digest:
                print(
                    f"Using existing immutable archive {destination.relative_to(ROOT)} "
                    f"({destination.stat().st_size} bytes, sha256 {digest})."
                )
                return 0
            raise ValueError(
                f"{destination} already exists but is not verified by the source manifest; "
                "move it aside explicitly before fetching"
            )

        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        resolved_url, size, tls_verified = download(
            url=source_config["archive_url"],
            destination=destination,
            allow_insecure_tls=args.allow_insecure_tls,
        )
        source = update_manifest(
            args.manifest,
            official_page=source_config["official_page"],
            resolved_url=resolved_url,
            archive=destination,
            tls_verified=tls_verified,
            retrieved_at=retrieved_at,
            corpus=corpus,
        )
        print(
            f"Downloaded {destination.relative_to(ROOT)} from {resolved_url}\n"
            f"- bytes: {size}\n"
            f"- sha256: {source['archive_sha256']}\n"
            f"- TLS certificate verified: {tls_verified}"
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"Corpus fetch failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
