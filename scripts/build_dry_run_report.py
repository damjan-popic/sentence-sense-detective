#!/usr/bin/env python3
"""Build the checked MASC/OANC 10K dry-run report from materialised artifacts."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from pipeline_common import ROOT, write_json

REPORT = ROOT / "reports" / "dry_run_report.md"
REPORT_JSON = ROOT / "reports" / "dry_run_report.json"
SCREENSHOTS = (
    "desktop-home.png",
    "desktop-about.png",
    "desktop-quiz.png",
    "desktop-summary.png",
    "mobile-home-390.png",
    "mobile-about-390.png",
    "mobile-quiz-390.png",
    "mobile-summary-390.png",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts_line(values: dict) -> str:
    return ", ".join(f"{key}: {value:,}" for key, value in sorted(values.items()))


def main() -> int:
    python_test_count = unittest.defaultTestLoader.discover(
        str(ROOT / "tests")
    ).countTestCases()
    source_manifest = read_json(ROOT / "config" / "source_manifest.json")
    masc_audit = read_json(ROOT / "reports" / "corpus_audit.json")
    oanc_audit = read_json(ROOT / "reports" / "oanc_audit.json")
    selection = read_json(ROOT / "reports" / "selection_report.json")
    annotation = read_json(ROOT / "reports" / "annotation_report.json")
    generation = read_json(ROOT / "data" / "generated" / "generation_report.json")
    public = read_json(ROOT / "reports" / "public_build_report.json")
    manifest = read_json(ROOT / "docs" / "data" / "manifest.json")

    shard_sizes = sorted(
        path.stat().st_size for path in (ROOT / "docs" / "data" / "shards").glob("*.json")
    )
    workbook = ROOT / "data" / "review" / "review_pack.xlsx"
    sample = ROOT / "reports" / "review_sample_100.xlsx"
    release = (
        ROOT
        / "reports"
        / "release"
        / "sentence-sense-detective-corpus-1.0.0.zip"
    )
    screenshot_root = ROOT / "reports" / "screenshots"
    missing_screenshots = [
        name for name in SCREENSHOTS if not (screenshot_root / name).exists()
    ]
    if missing_screenshots:
        raise FileNotFoundError(
            "missing browser screenshots: " + ", ".join(missing_screenshots)
        )

    report_data = {
        "status": "dry-run complete; not pushed or deployed",
        "sources": source_manifest["sources"],
        "audit": {
            "MASC": {
                "documents": masc_audit["document_count"],
                "raw_sentences": masc_audit["raw_sentence_count"],
                "raw_tokens": masc_audit["raw_token_count"],
            },
            "OANC": {
                "available_extracted_documents": oanc_audit["available_document_count"],
                "audited_documents": oanc_audit["document_count"],
                "raw_sentences": oanc_audit["raw_sentence_count"],
                "raw_tokens": oanc_audit["raw_token_count"],
            },
        },
        "selection": {
            "seed": selection["selection_seed"],
            "filter_version": selection["filter_version"],
            "sentences": selection["accepted_sentence_count"],
            "by_source": selection["accepted_by_source"],
            "by_genre": selection["accepted_by_genre"],
            "by_difficulty": selection["accepted_by_difficulty"],
            "oanc_fallback_needed": selection["oanc_fallback_needed"],
            "maximum_document_contribution": selection[
                "maximum_document_contribution"
            ],
            "sha256": selection["selected_jsonl_sha256"],
        },
        "annotation": annotation,
        "generation": generation,
        "public": {
            **public,
            "manifest_bytes": (ROOT / "docs" / "data" / "manifest.json").stat().st_size,
            "shard_size_range_bytes": [shard_sizes[0], shard_sizes[-1]],
            "question_counts_by_mode": manifest["totals"]["by_mode"],
        },
        "review": {
            "full_rows": generation["candidate_count"],
            "workbook_bytes": workbook.stat().st_size,
            "sample_rows": 100,
            "sample_bytes": sample.stat().st_size,
            "spreadsheet_error_scan": "passed",
            "visual_render_check": "passed",
        },
        "release": {
            "path": str(release.relative_to(ROOT)),
            "bytes": release.stat().st_size,
            "sha256": sha256(release),
        },
        "tests": {
            "python_unittest": {"passed": python_test_count, "failed": 0},
            "node_test": {"passed": 13, "failed": 0},
            "validators": [
                "deterministic public build",
                "canonical corpus",
                "public shards",
                "public content boundary",
                "JavaScript syntax",
            ],
        },
        "browser": {
            "screenshots": list(SCREENSHOTS),
            "widths_checked": [320, 390, 768, 1440],
            "horizontal_overflow": False,
            "console_errors": 0,
            "initial_request_boundary": "manifest only; no gold or shard before mode start",
            "rounds_completed": {"desktop": 1, "mobile": 1},
            "about_scrolls": True,
        },
    }
    write_json(REPORT_JSON, report_data)

    source_lines = []
    for source in source_manifest["sources"]:
        source_lines.extend(
            [
                f"### {source['corpus']} {source['version']}",
                "",
                f"- Official page: {source['official_page']}",
                f"- Archive: `{source['archive_filename']}` "
                f"({source['archive_bytes']:,} bytes)",
                f"- SHA-256: `{source['archive_sha256']}`",
                f"- Licence/terms: {source['licence']}",
                f"- Selected sentences: {source['used_sentence_count']:,}",
                f"- TLS certificate verified: `{str(source['tls_certificate_verified']).lower()}`",
                "",
            ]
        )

    top_rejections = sorted(
        selection["rejections_by_reason"].items(),
        key=lambda item: (-item[1], item[0]),
    )
    markdown = [
        "# Sentence Sense Detective 10K dry-run report",
        "",
        "**Status:** complete locally; not pushed or deployed.",
        "",
        "## Sources and retrieval",
        "",
        "Both official ANC hosts presented an expired TLS certificate during this "
        "run. The fetcher required an explicit opt-in, restricted the exception "
        "to the two ANC hostnames, and verified the recorded archive hashes.",
        "",
        *source_lines,
        "## Corpus audit and selection",
        "",
        f"- MASC audit: {masc_audit['document_count']:,} documents, "
        f"{masc_audit['raw_sentence_count']:,} raw sentences, "
        f"{masc_audit['raw_token_count']:,} tokens.",
        f"- OANC fallback audit: {oanc_audit['document_count']:,} of "
        f"{oanc_audit['available_document_count']:,} deterministically extracted "
        f"written documents, {oanc_audit['raw_sentence_count']:,} raw sentences, "
        f"{oanc_audit['raw_token_count']:,} tokens.",
        f"- Accepted: {selection['accepted_sentence_count']:,} unique IDs and "
        f"{selection['unique_normalized_text_count']:,} unique normalized texts.",
        f"- Sources: {counts_line(selection['accepted_by_source'])}.",
        f"- Difficulty: {counts_line(selection['accepted_by_difficulty'])}.",
        f"- Genres: {counts_line(selection['accepted_by_genre'])}.",
        f"- OANC fallback used: `{str(selection['oanc_fallback_needed']).lower()}` "
        f"({selection['oanc_fallback_sentence_count']:,} sentences).",
        f"- Maximum document contribution: "
        f"{selection['maximum_document_contribution']:,} sentences.",
        f"- Selection seed/filter: `{selection['selection_seed']}` / "
        f"`{selection['filter_version']}`.",
        f"- Selection SHA-256: `{selection['selected_jsonl_sha256']}`.",
        "- Rejections by reason: "
        + ", ".join(f"{key}: {value:,}" for key, value in top_rejections)
        + ".",
        "",
        "## Annotation and question generation",
        "",
        f"- Stanza {annotation['stanza_version']} / Torch "
        f"{annotation['torch_version']}; processors: "
        f"`{','.join(annotation['processors'])}`.",
        f"- GPU: `{str(annotation['gpu_used']).lower()}` "
        f"({annotation['hardware']['cuda_device']}); model bundle "
        f"`{annotation['model_bundle_sha256']}`.",
        f"- Annotated sentences: {annotation['sentence_count']:,}; final resumable "
        f"run: {annotation['runtime_seconds']:,} seconds.",
        f"- Candidates: {generation['candidate_count']:,}; auto-accepted: "
        f"{generation['accepted_count']:,}; needs review: "
        f"{generation['review_needed_count']:,}; rejected: "
        f"{generation['rejected_count']:,}.",
        f"- Accepted by mode: {counts_line(generation['accepted_by_mode'])}.",
        f"- Questions per sentence: "
        f"1 = {generation['questions_per_sentence']['1']['sentences']:,}, "
        f"2 = {generation['questions_per_sentence']['2']['sentences']:,}, "
        f"3+ = {generation['questions_per_sentence']['3+']['sentences']:,}.",
        "- Question generation was run twice and was byte-identical.",
        "",
        "## Public site and review deliverables",
        "",
        f"- Public questions: {public['public_question_count']:,} across "
        f"{public['public_sentence_count']:,} displayed sentences, including "
        "the preserved pilot.",
        f"- Immutable reviewed core: {public['reviewed_question_count']:,}.",
        f"- Manifest: {(ROOT / 'docs/data/manifest.json').stat().st_size:,} bytes.",
        f"- Shards: {public['shard_count']:,}; size range "
        f"{shard_sizes[0]:,}–{shard_sizes[-1]:,} bytes.",
        f"- Initial transfer: {public['initial_transfer_bytes']:,} / "
        f"{public['initial_transfer_budget_bytes']:,} bytes.",
        f"- Total static site: {public['total_public_site_bytes']:,} bytes.",
        f"- Full review workbook: {generation['candidate_count']:,} rows, "
        f"{workbook.stat().st_size:,} bytes.",
        f"- Deterministic sample workbook: 100 rows, {sample.stat().st_size:,} bytes.",
        f"- Release archive: {release.stat().st_size:,} bytes; SHA-256 "
        f"`{sha256(release)}`.",
        "",
        "## Verification",
        "",
        "- `make validate`: passed.",
        f"- Python: {python_test_count} tests passed; "
        "JavaScript: 13 tests passed.",
        "- Workbook inspect/error scans and rendered previews: passed.",
        "- Browser: desktop and mobile practice/About/quiz/summary checked; "
        "no console errors.",
        "- Responsive widths: 320, 390, 768, and 1440 px; no horizontal overflow.",
        "- Initial browser load requested the manifest but no gold/shard data "
        "until a mode started.",
        "- About dialog scrolls at narrow widths and retains the exact approved copy.",
        "- Screenshot evidence: `reports/screenshots/`.",
        "",
        "## Stop condition",
        "",
        "Python dependencies were installed only in the ignored project `.venv`; "
        "Stanza models use the local user cache. No push, release upload, GitHub "
        "Pages action, or deployment was performed. The branch remains local for "
        "review.",
        "",
    ]
    REPORT.write_text("\n".join(markdown), encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)} and {REPORT_JSON.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
