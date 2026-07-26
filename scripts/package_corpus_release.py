#!/usr/bin/env python3
"""Create a deterministic versioned corpus release artifact and checksums."""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

from pipeline_common import ROOT

VERSION = "1.0.0"
OUTPUT = (
    ROOT
    / "reports"
    / "release"
    / f"sentence-sense-detective-corpus-{VERSION}.zip"
)
FILES = (
    ROOT / "data" / "corpus" / "sentences_10k.jsonl",
    ROOT / "data" / "corpus" / "sentences_10k.conllu",
    ROOT / "reports" / "selection_report.json",
    ROOT / "reports" / "annotation_report.json",
    ROOT / "config" / "source_manifest.json",
    ROOT / "THIRD_PARTY_NOTICES.md",
)


def main() -> int:
    missing = [path for path in FILES if not path.exists()]
    if missing:
        print(
            "Corpus release packaging failed; missing: "
            + ", ".join(str(path.relative_to(ROOT)) for path in missing),
            file=sys.stderr,
        )
        return 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".zip.part")
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        for path in FILES:
            info = zipfile.ZipInfo(
                f"sentence-sense-detective-corpus-{VERSION}/"
                f"{path.relative_to(ROOT).as_posix()}",
                date_time=(2026, 7, 26, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    temporary.replace(OUTPUT)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    checksum = OUTPUT.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {OUTPUT.name}\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size} bytes, "
        f"sha256 {digest})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
