# AGENTS.md — Sentence Sense Detective

These instructions apply to every task in this repository. `CODEX_HANDOVER_FORMAL_REMAP_ENGINE.md` is the newest authority for the formal remapping architecture; read it after this file, `CODEX_HANDOVER.md`, and `CODEX_HANDOVER_MASC_OANC_10K.md` before changing the corpus architecture, rule profile, or public site.

## Product and content locks

- Preserve the highlighted-target interface, ten-question rounds, first-attempt scoring, one zero-point retry, zero-point reveal, streaks, summaries, and mistake review.
- Preserve all 106 teacher-reviewed mappings exactly once. `Operator` remains a separate category, and the visible expert-review guard remains a valid output.
- Never silently change a reviewed ID, source ID, answer, target, prompt, explanation, terminology choice, or review guard. A reviewed change requires a written rationale, changelog entry, and regression test.
- Keep word class, sentence element, clause class, marker type, clause structure, and clause function as separate pedagogical dimensions.
- Use “formal pedagogical remapping”, “pedagogical grammar layer”, “pedagogical analysis”, or “Universal Pedagogical Tag Set”; never call it a departmental schema.
- Do not imply that technical annotation labels are classroom grammar labels.

## Public explanation of remapping

- Formal pedagogical remapping is a principal scientific and methodological contribution of the project. It must be described prominently and accurately on the home page, in the About dialog, and in the Grammar Handbook.
- The public explanation may name Stanza and Universal Dependencies and may describe the high-level sequence: corpus sentence → source analysis → versioned pedagogical remapping profile → reviewed or publishable pedagogical annotation → practice question.
- The public explanation may report verified aggregate results, including the 106-case reviewed contract, exact replay, 10,000-sentence corpus, publish/review counts, and the distinction between direct correspondence, structurally derived analysis, and expert review.
- Do not reduce remapping to front-end relabelling. Explain that it may combine structural evidence, lexical conditions, exclusions, complete target-span reconstruction, rule priority, conflict handling, provenance, and abstention.
- Do not use named drafting placeholders such as “to be expanded/amended by Martin Grad” or `[MARTIN: ...]`. Use neutral wording such as **Content in preparation**, **Expanded content coming**, or **Section in development**.

## Public boundary

- Exercises, choices, feedback, summaries, and public question data must not contain raw dependency relations, formal rule IDs, source-case IDs, confidence classes, implementation statuses, private notes, reviewer comments, or source spreadsheet fields.
- Technical methodology belongs only on the public explanatory pages (`docs/index.html` and `docs/handbook.html`), not in the exercise interface or question shards.
- Keep internal annotations, comments, rules, provenance-maintenance fields, and review fields outside `docs/`.
- Public methodology should distinguish the computational source representation from the teaching terminology. Students are not expected to learn UD labels.
- Escape all content inserted into HTML.

## Data architecture

- Canonical records are JSONL under `data/corpus`, `data/annotations`, and `data/questions`.
- Formal remapping rules are versioned under `config/remap/<language>/`; compiled profiles and materialised candidates remain separate from question presentation.
- Public delivery uses `docs/data/manifest.json`, `docs/data/gold.json`, and deterministic lazy-loaded files under `docs/data/shards/`. Do not restore a monolithic browser payload.
- Targets are Unicode code-point half-open ranges. Multiple spans represent discontinuous targets.
- Every sentence requires source, licence, and attribution metadata. Rights that are pending, blocked, unknown, or incompatible must block public output.
- Use MASC 3.0.0 from the official ANC source first and the written OANC only for the documented shortfall after filtering. Never scrape replacement web text or fabricate corpus sentences.
- Public shards must remain under 500 KB uncompressed. Initial HTML, CSS, JavaScript, and manifest transfer must remain under 500 KB uncompressed, excluding optional images.

## Interface and deployment

- Keep the static, no-build, vanilla HTML/CSS/JavaScript path.
- Maintain keyboard access, visible focus, semantic HTML, readable contrast, reduced-motion support, and no horizontal overflow at 390 px.
- Initial page load fetches the manifest only. Mode selection loads shards with accessible Loading, Retry, and Return home states.
- A round must contain ten unique question IDs and ten unique sentence IDs, use the selected mode only, retain the reviewed-core sampling policy, and keep recent history at no more than 250 question IDs and 150 sentence IDs per mode.
- Keep corpus-only dependencies in a project `.venv` and `requirements-corpus.txt`.
- Do not push, deploy, change Pages settings, or add a custom domain without explicit approval. Repository-content edits requested directly by Damjan are permitted, but report the exact files and validation status honestly.

## Required checks

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

For UI changes, serve `docs/` and inspect desktop practice, the public remapping feature, the About methodology view, the Handbook remapping chapter, mobile practice at 390 × 844, keyboard operation, reduced motion, all scoring paths, the browser console, and page errors.
