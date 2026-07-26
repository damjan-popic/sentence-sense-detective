# AGENTS.md — Sentence Sense Detective

These instructions apply to every task in this repository. `CODEX_HANDOVER_10K_OPEN_CORPUS.md` is the newest authoritative brief; read it in full before changing the corpus architecture or public site.

## Product and content locks

- Preserve the highlighted-target interface, ten-question rounds, first-attempt scoring, one zero-point retry, zero-point reveal, streaks, summaries, and mistake review.
- Preserve all 106 teacher-reviewed mappings exactly once. `Operator` remains a separate category, and the visible manual-review guard remains a valid output.
- Never silently change a reviewed ID, source ID, answer, target, prompt, explanation, terminology choice, or review guard. A reviewed change requires a written rationale, changelog entry, and regression test.
- Keep word class, sentence element, clause class, marker type, clause structure, and clause function as separate pedagogical dimensions.
- Use “pedagogical grammar layer”, “pedagogical analysis”, or “Universal Pedagogical Tag Set”; never call it a departmental schema.
- Do not imply that technical annotation labels are classroom grammar labels.

## Public boundary

- The only public allowance for `Stanza`, `Universal Dependencies`, or `UD` is the exact paragraph between `methodology-note:start` and `methodology-note:end` in `docs/index.html`.
- Exercises, choices, feedback, summaries, and public question data must not contain raw dependency labels, transformation tables, confidence classes, private notes, reviewer identity, or development jargon.
- Keep internal annotations, comments, rules, provenance maintenance fields, and review fields outside `docs/`.
- Escape all content inserted into HTML.

## Data architecture

- Canonical records are JSONL under `data/corpus`, `data/annotations`, and `data/questions`.
- Public delivery uses `docs/data/en/manifest.json` and deterministic lazy-loaded shards. Do not restore a monolithic browser payload.
- Targets are Unicode code-point half-open ranges. Multiple spans represent discontinuous targets.
- Every sentence requires source, licence, and attribution metadata. Rights that are pending, blocked, unknown, or incompatible must block public output.
- Do not scrape, invent, generate, or silently choose a 10,000-sentence corpus. Use only team-supplied text with confirmed rights.
- Public shards target 500 KB or less and fail above 1 MB. The manifest fails above 250 KB; `docs/` fails above 250 MB.

## Interface and deployment

- Keep the static, no-build, vanilla HTML/CSS/JavaScript path.
- Maintain keyboard access, visible focus, semantic HTML, readable contrast, reduced-motion support, and no horizontal overflow at 390 px.
- Initial page load fetches the manifest only. Mode selection loads shards with accessible Loading, Retry, and Return home states.
- A round must contain ten unique question IDs and ten unique sentence IDs, use the selected mode only, retain the reviewed-core sampling policy, and keep recent history at no more than 500 IDs per mode.
- Do not install dependencies, push, deploy, change Pages settings, or add a custom domain without explicit approval.

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

For UI changes, serve `docs/` and inspect desktop practice, the About methodology view, mobile practice at 390 × 844, keyboard operation, reduced motion, all scoring paths, the browser console, and page errors.
