# Codex handover — Sentence Sense Detective

`CODEX_HANDOVER_10K_OPEN_CORPUS.md` supersedes this handover and is the authoritative implementation brief. Read that file and `AGENTS.md` in full.

## Current implemented baseline

- Static student-facing interface with Parts of Speech, Sentence Elements, and Clauses modes.
- Ten-question rounds with first-attempt scoring, one learning retry, reveal, streaks, summary, and mistake review.
- 156 preserved pilot questions over 92 unique sentences.
- 106 teacher-reviewed questions and 50 provisional Parts of Speech questions.
- Exact migration from target text/occurrence matching to Unicode code-point offsets, guarded by legacy contract hashes.
- Separate canonical sentence, machine-annotation, pedagogical-annotation, question, provenance, and public schemas.
- Deterministic public manifest and lazy shards; no monolithic browser question payload.
- Reviewed-core sampling, unique sentence/question selection, a bounded recent-history list, and two-shard browser cache.
- Supplied-corpus ingestion, local pre-annotation entry point, conservative candidate/question building, file-based review corrections, validation, and a metadata-only 10,000-sentence capacity report.
- Supplied vector logo, complete favicon set, and the exact public methodology/aim copy.

## Locked pilot choices

- `SE-P-02` highlights **Did** and uses **Operator**.
- `REVIEW-01` uses **Context needed** and keeps manual review visible as a valid outcome.
- Round size is 10.
- Only first-attempt correct answers score one point.
- Retry and reveal score zero; there are no negative points.
- Progress stays in browser storage.

## Stop condition

No 10,000-sentence source corpus has been supplied or created. Do not source, scrape, fabricate, generate, or publish one. The project team must supply corpus text and confirm its licensing before the pipeline can materialize it.
