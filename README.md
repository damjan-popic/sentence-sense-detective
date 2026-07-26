# Sentence Sense Detective

**Spot it. Name it. Make it stick.**

Sentence Sense Detective is a dependency-free grammar practice site. The English pilot contains 156 questions over 92 unique sentences:

- 50 provisional Parts of Speech questions;
- 44 teacher-reviewed Sentence Elements questions;
- 62 teacher-reviewed Clauses questions.

The 106 reviewed cases are preserved exactly. Students complete ten-question rounds with one learning retry, explanations, summaries, and mistake review. Progress stays in the browser; there is no account, backend, analytics, or tracking.

## Run locally

```bash
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. Serving over HTTP is required because the browser loads the manifest and selected question shards with `fetch`.

## Validate

```bash
python3 scripts/build_public_shards.py --check
python3 scripts/validate_corpus.py
python3 scripts/validate_public_shards.py
python3 scripts/validate_data.py
python3 -m unittest discover -s tests -v
node --check docs/assets/round-state.js
node --check docs/assets/question-bank.js
node --check docs/assets/app.js
node --test tests/test_round_state.js tests/test_question_bank.js
```

## Data architecture

Canonical records are newline-delimited JSON and keep the distinct data layers separate:

```text
data/corpus/en/                     source sentences and corpus manifest
data/annotations/en/                internal machine and pedagogical annotations
data/questions/en/                  reviewed/provisional questions and configuration
data/sources/en-sources.json         provenance, licence, and rights declarations
docs/data/en/manifest.json           initial browser payload
docs/data/en/<mode>/*.json           lazy-loaded public question shards
schema/                              contracts for every record/public layer
```

Targets use Unicode code-point half-open ranges (`start`, `end`). Discontinuous targets use multiple spans. Public shards contain only the fields needed by the exercise.

The public builder is deterministic, packs at most 400 questions per shard, targets at most 500 KB uncompressed, and refuses a shard above 1 MB. The browser initially fetches only the manifest, then loads one or more shards after a mode is selected. A round never repeats a question or source sentence.

## Supplied-corpus pipeline

The ingestion path accepts a team-supplied `.tsv` or `.jsonl` file with:

```text
sentence_id	language	text	source_id	document_id	licence	attribution
```

Start from `examples/corpus-input-template.tsv`; replace every placeholder with the supplied corpus’s actual provenance and rights information.

Example dry run:

```bash
python3 scripts/ingest_sentences.py supplied.tsv \
  --output-dir /tmp/sentence-sense-corpus --dry-run
```

The pipeline validates IDs, language tags, text, provenance, and licence metadata; reports exact and near duplicates separately; preserves source text; and writes 500-sentence canonical shards. Subsequent stages are:

```bash
python3 scripts/preannotate_stanza.py --input-dir CORPUS --output MACHINE.jsonl --dry-run
python3 scripts/build_pedagogical_candidates.py \
  --sentences SENTENCES.jsonl --machine-annotations MACHINE.jsonl \
  --output CANDIDATES.jsonl --review-queue REVIEW.json
python3 scripts/build_question_bank.py build \
  --sentences SENTENCES.jsonl --annotations CANDIDATES.jsonl \
  --output QUESTIONS.jsonl
```

`preannotate_stanza.py` never installs a package, downloads a model, or fetches a resource. Its non-dry-run path only uses an already-approved local environment. Candidate records remain provisional. Human review uses `build_question_bank.py export-review` and `apply-corrections`, with stable IDs, mandatory rationales, change reports, and idempotent updates.

## 10,000-sentence stop condition

No 10,000-sentence corpus is included. The project team must supply the source text and confirm its licence/publication status. The checked capacity report at `reports/capacity-10000.json` is metadata only: 10,000 sentences would occupy 20 canonical shards at 500 records each. Question count and byte totals intentionally remain unknown until a licensed corpus is supplied.

## Licensing

- Software: `LICENSE-CODE` (MIT).
- Pedagogical question content and explanations: `LICENSE-CONTENT`.
- Source-sentence publication rights: recorded per source in `data/sources/en-sources.json`.

Do not publish a new source corpus when its rights are pending, blocked, unknown, or incompatible. The public builder enforces this boundary.

## GitHub Pages

The site remains static and deployable from `docs/` through `.github/workflows/pages.yml`. The workflow validates canonical data, deterministic shards, tests, JavaScript, and size budgets before deployment.
