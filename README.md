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
make remap-all
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
config/remap/en/                             versioned declarative remap source
data/remap/en/compiled_rules.json            compiled executable profile
data/remap/en/pedagogical_candidates_10k.jsonl.gz
                                             materialised formal remap output
data/generated/                              compressed candidates and accepted questions
data/gold/                                   immutable 106-case reference index
data/review/review_pack.xlsx                 full human-review workbook
reports/remap_manual_review_sample.xlsx      stratified review-only sample
reports/remap_*.json                         coverage, replay, impact reports
reports/release/                             versioned corpus download artifact
```

`scripts/import_review_corrections.py` validates review decisions, IDs,
controlled labels, target offsets, reviewer/date metadata, and conflicting
duplicates. It performs no write without `--apply`, logs every applied change,
and cannot modify the 106 reviewed gold cases.

## Pedagogical remapping

The formal remapper is a separate, versioned stage between Stanza and question
presentation. Source rules live in JSON-compatible YAML under
`config/remap/en/`; `scripts/compile_remap_rules.py` validates and compiles
them, `scripts/formal_remap_engine.py` applies them to structural match events,
and `scripts/remap_stanza_annotations.py` materialises the result. The question
generator consumes only those materialised records and contains no direct
UD-to-pedagogical label mappings.

Each Sentence Elements or Clauses output records its formal rule, source case
IDs, profile hash, matched Stanza evidence, and pinned model metadata. Parts of
Speech uses a distinct provisional profile because the reviewed 106 cases are
not a complete word-class gold set. Sentence element, clause type, marker,
structure, and function remain separate dimensions.

The imported Martin-reviewed contract contains exactly 106 cases with the
authoritative 26 direct, 60 rule-based, and 20 manual-review decisions.
Replaying the pinned Stanza 1.14.0 fixtures matches all 106 answers, actions,
and spans. No manual-review case can publish automatically. `CL-MARK-10`
remains an explicit zero-marker review guard; no synthetic `∅` is inserted
into corpus text.

Only high-confidence candidates enter the public shards. Constructional or
lexical ambiguity stays in the full review workbook with a rule-specific
reason; manual review is therefore an explicit output rather than hidden
certainty.

The former 34,858-question heuristic bank is preserved under
`data/generated/legacy_handcoded_a1ed4bd/` for audit and comparison only. It is
not an input to the formal public bank.

## Browser data architecture

The static site loads `docs/data/manifest.json`, then only enough mode-specific
files under `docs/data/shards/` to assemble a round. `docs/data/gold.json` keeps
the reviewed cases available at the manifest’s 15% sampling weight. Each target
uses Unicode code-point half-open offsets, each shard is at most 400 questions
and below 500 KB uncompressed, and recent browser history is bounded. Ordinary
rounds sample across available labels and subskills and cap any answer label at
three when alternatives exist.

The full selected corpus is kept out of the initial page and packaged as a
versioned release artifact. Source, licence, attribution, and download details
are documented in `THIRD_PARTY_NOTICES.md` and the site’s Credits page.

## Validate

```bash
make validate
```

This checks the canonical corpus, all public files and hashes, the exact
106-case contract and replay, manual guards, formal provenance and conflicts,
deterministic public output, Python tests, JavaScript syntax/tests, balanced
round sampling, public terminology boundaries, and size budgets.

## Licensing

- Software: `LICENSE-CODE` (MIT).
- Pedagogical question content and explanations: `LICENSE-CONTENT`.
- MASC/OANC sentences: their source licences and attribution terms, recorded in
  `config/source_manifest.json` and `THIRD_PARTY_NOTICES.md`.

The site remains static and deployable from `docs/` through the checked GitHub
Pages workflow.
