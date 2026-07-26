# Sentence Sense Detective

**Spot it. Name it. Make it stick.**

Sentence Sense Detective is a dependency-free grammar practice site. Its English
bank combines an immutable core of 106 Martin-reviewed Sentence Elements and
Clauses cases with questions generated conservatively from exactly 10,000
licensed MASC/OANC sentences. Students complete ten-question rounds with one
learning retry, explanations, summaries, and mistake review. Progress stays in
the browser; there is no account, backend, analytics, or tracking.

## Run locally

```bash
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. HTTP is required because the browser fetches the
manifest and selected question shards on demand.

## Reproduce the corpus build

The source and model pipeline is intentionally separate from the static site.
Create a Python 3.12 virtual environment, then install the pinned packages:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-corpus.txt
```

The official ANC hosts currently present an expired TLS certificate. The fetch
commands therefore require the explicit `--allow-insecure-tls` opt-in encoded in
the Make targets, restrict that exception to `anc.org` and `www.anc.org`, record
the condition in `config/source_manifest.json`, and still verify fixed archive
SHA-256 values after download.

```bash
make corpus-fetch
make corpus-models
make corpus-audit
make corpus-fetch-oanc
make corpus-audit-oanc
make corpus-select
make corpus-annotate
make corpus-generate
make corpus-review-pack
make corpus-build-public
make corpus-package
```

MASC 3.0.0 is always tried first. The written OANC is used only for the
deterministic shortfall after filtering and per-document caps. Raw archives,
extractions, audit candidates, resumable annotation batches, and workbook
previews live under ignored `external/`; they are never public site payloads.

The materialised outputs are:

```text
data/corpus/sentences_10k.jsonl             selected sentences and provenance
data/corpus/sentences_10k.annotations.jsonl local Stanza output
data/corpus/sentences_10k.conllu             portable CoNLL-U export
data/generated/                              candidates and accepted questions
data/gold/                                   immutable 106-case reference index
data/review/review_pack.xlsx                 full human-review workbook
reports/review_sample_100.xlsx               deterministic review sample
reports/release/                             versioned corpus download artifact
```

`scripts/import_review_corrections.py` validates review decisions, IDs,
controlled labels, target offsets, reviewer/date metadata, and conflicting
duplicates. It performs no write without `--apply`, logs every applied change,
and cannot modify the 106 reviewed gold cases.

## Browser data architecture

The static site loads `docs/data/manifest.json`, then only enough mode-specific
files under `docs/data/shards/` to assemble a round. `docs/data/gold.json` keeps
the reviewed cases available at the manifest’s 15% sampling weight. Each target
uses Unicode code-point half-open offsets, each shard is at most 400 questions
and below 500 KB uncompressed, and recent browser history is bounded.

The full selected corpus is kept out of the initial page and packaged as a
versioned release artifact. Source, licence, attribution, and download details
are documented in `THIRD_PARTY_NOTICES.md` and the site’s Credits page.

## Validate

```bash
make validate
```

This checks the canonical corpus, all public files and hashes, the exact
106-case gold contract, deterministic public output, Python tests, JavaScript
syntax/tests, public terminology boundaries, and size budgets.

## Licensing

- Software: `LICENSE-CODE` (MIT).
- Pedagogical question content and explanations: `LICENSE-CONTENT`.
- MASC/OANC sentences: their source licences and attribution terms, recorded in
  `config/source_manifest.json` and `THIRD_PARTY_NOTICES.md`.

The site remains static and deployable from `docs/` through the checked GitHub
Pages workflow.
