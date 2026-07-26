# Changelog

## 1.0.0

- Guarded fused and nominal relatives, independent determinatives, and copular
  verbs so ambiguous automatic analyses stay out of the public bank, and
  excluded boundary punctuation from generated highlights.
- Added a reproducible, resumable MASC 3.0.0-first corpus pipeline with a
  written-OANC fallback, exact provenance, deterministic selection, and 10,000
  unique English sentences.
- Ran pinned local Stanza annotation and exported versioned JSONL and CoNLL-U
  artifacts without exposing annotation internals in student exercises.
- Generated conservative questions from the existing controlled vocabulary,
  retained every sentence, and separated auto-accepted and review-needed items.
- Added the full review workbook, deterministic 100-question review sample,
  strict correction importer, and immutable index for all 106 reviewed cases.
- Replaced the pilot-scale public bank with a direct manifest, reviewed gold
  file, and bounded mode-specific shards suitable for GitHub Pages.
- Added source credits, licences, release packaging, public size budgets,
  deterministic reporting, and corpus-specific regression tests.
- Integrated the final supplied logo/favicon family and exact About copy with a
  narrow methodology-term allowlist.

## 0.3.0

- Migrated all 156 targets from text/occurrence lookup to Unicode code-point offsets while preserving the complete legacy question and highlight fingerprints.
- Split 92 source sentences, 156 pedagogical annotations, 106 reviewed questions, and 50 provisional questions into separate canonical JSONL layers.
- Replaced the monolithic browser payload with a deterministic manifest and three lazy-loaded public shards.
- Added unique-question/unique-sentence round selection, reviewed-core sampling, bounded recent history, a two-shard cache, and recoverable loading states.
- Integrated the supplied vector logo, SVG/PNG favicon set, web manifest, and exact About methodology/aim copy.
- Added a privacy-safe content-correction link and issue template.
- Added supplied-corpus ingestion, local pre-annotation, conservative candidate/question generation, file-based correction, canonical/public validation, and deterministic build checks.
- Added a metadata-only 10,000-sentence capacity report. No new corpus was sourced, generated, or published.
- Expanded regression coverage for data preservation, offsets, public boundaries, shard integrity, sampling, loading recovery, pipeline idempotence, and size budgets.

## 0.2.1

- Audited all 156 questions and preserved every reviewed ID, target, answer, and terminology choice.
- Replaced implausible distractors with fixed four-choice contrast sets that always include the answer.
- Rewrote thin or internal-facing explanations as student-facing grammar guidance.
- Removed internal review counts, source statuses, and preparation language from the public payload.
- Added an immutable reviewed-contract regression fingerprint and exact source-ID coverage checks.
- Extracted round scoring into a tested state engine covering first answers, retries, reveals, streaks, and finalization.
- Improved focus management, progress semantics, corrupt-storage handling, keyboard shortcuts, and reduced-motion behaviour.
- Verified full rounds in all three modes at desktop and 390 × 844 mobile widths, including mistake review, refresh persistence, and reset.

## 0.2.0-scaffold

- Renamed the product to **Sentence Sense Detective**.
- Rebuilt the public interface as a grammar quiz rather than a technical demonstrator.
- Added Parts of Speech, Sentence Elements, and Clauses modes.
- Preserved all 106 reviewed source cases as pedagogical questions.
- Added 50 provisional parts-of-speech questions drawn from the same source sentences.
- Added ten-question rounds, first-attempt scoring, one retry, streaks, summaries, mistake review, and browser-local progress.
- Made `Operator` a separate answer category.
- Removed all technical preparation terminology from the public site.
