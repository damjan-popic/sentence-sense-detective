# Codex handover — Sentence Sense Detective

`CODEX_HANDOVER_FORMAL_REMAP_ENGINE.md` is the newest authority for generated
questions. Read `AGENTS.md`, this file, `CODEX_HANDOVER_MASC_OANC_10K.md`, and
the formal-remap handover in that order.

## Current implemented baseline

- Static student-facing interface with Parts of Speech, Sentence Elements, and Clauses modes.
- Ten-question rounds with first-attempt scoring, one learning retry, reveal, streaks, summary, and mistake review.
- 156 preserved pilot questions over 92 unique sentences.
- 106 teacher-reviewed questions and 50 provisional Parts of Speech questions.
- Exact migration from target text/occurrence matching to Unicode code-point offsets, guarded by legacy contract hashes.
- Separate canonical sentence, machine-annotation, pedagogical-annotation, question, provenance, and public schemas.
- Deterministic public manifest and lazy shards; no monolithic browser question payload.
- Reviewed-core sampling, unique sentence/question selection, a bounded recent-history list, and two-shard browser cache.
- Materialised 10,000-sentence MASC/OANC corpus and pinned local Stanza
  annotation retained unchanged.
- Versioned declarative remap registry and compiled profile, separate formal
  engine, materialised remap output, and presentation-only question generator.
- Exact 106/106 replay of the Martin-reviewed contract with the authoritative
  26 direct / 60 rule-based / 20 manual-review inventory and zero manual cases
  auto-published.
- Separate provisional Parts of Speech profile; internal profile/rule/source
  case/Stanza/model provenance on every generated candidate.
- Quarantined 34,858-question legacy heuristic bank, complete old-versus-new,
  coverage, replay, rule-distribution, and formal review reports.
- Balanced public rounds, full six-sheet review pack, static manifest/shard
  bank, and release packaging.
- Supplied vector logo, complete favicon set, and the exact public methodology/aim copy.

## Locked pilot choices

- `SE-P-02` highlights **Did** and uses **Operator**.
- `REVIEW-01` uses **Context needed** and keeps manual review visible as a valid outcome.
- Round size is 10.
- Only first-attempt correct answers score one point.
- Retry and reveal score zero; there are no negative points.
- Progress stays in browser storage.

## Current corpus authority

The MASC/OANC handover authorizes local acquisition from the official ANC
source, with MASC 3.0.0 first and written OANC only as a documented fallback.
The formal mapping layer is implemented locally and regression-replayed against
all 106 reviewed cases. Four teacher comments whose referents cannot be
recovered from the supplied extraction are recorded explicitly in
`reports/remap_contract_coverage.*`; they were not silently guessed. The
rebuild command never pushes or deploys; publication remains a separate
explicit action after the formal reports and review sample are approved.
