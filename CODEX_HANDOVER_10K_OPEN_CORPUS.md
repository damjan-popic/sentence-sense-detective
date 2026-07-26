# Codex handover — Sentence Sense Detective: open 10,000-sentence corpus

## Authority and working rules

Work in `damjan-popic/sentence-sense-detective`.

Read `AGENTS.md`, `CODEX_HANDOVER.md`, `README.md`, all schemas/build scripts/tests, and the current `docs/` implementation before editing. Treat this file as the newest authoritative brief where it differs from earlier handovers.

Create a feature branch. Do not push, deploy, install packages, download models, call external services, or obtain a corpus without the user's explicit approval. Show the diff and all test results first.

This is a controlled scale-up, not a redesign. Keep the existing warm interface and student workflow.

## Locked product decisions

- Title: **Sentence Sense Detective**.
- Current profile: **English pilot**.
- Modes: Parts of Speech; Sentence Elements; Clauses (advanced).
- Highlighted-target interaction only.
- Ten questions per normal round.
- First-attempt correct = 1 point.
- One unscored learning retry.
- Reveal = 0 points; no negative points.
- Streak = consecutive first-attempt correct answers.
- End-of-round score, percentage, subskill breakdown, explanations, and Review mistakes.
- Progress remains in browser storage only.
- No login, backend, leaderboard, analytics, tracking, advertising, or paid feature.
- `Operator` remains a separate sentence-element answer category.
- Static vanilla HTML/CSS/JavaScript deployed from `docs/` through GitHub Pages.

## Deliverables

1. Replace the emoji brand mark with the supplied vector logo.
2. Add SVG/PNG favicons, Apple touch icon, PWA icons, and web manifest.
3. Expand About with an honest account of the internal Stanza/UD preparation layer and the open multilingual aim.
4. Refactor the bank from one monolithic browser payload to a manifest plus lazily fetched question shards.
5. Establish separate schemas and storage for source sentences, internal annotations, pedagogical annotations, questions, and public shards.
6. Preserve the existing 106 instructor-reviewed cases as an immutable reviewed core.
7. Preserve the existing 50 provisional POS questions until corrected through the documented content workflow.
8. Add a discreet, privacy-preserving “Report this question” link using stable IDs.
9. Update tests, validation, README, AGENTS.md, CHANGELOG.md, and deployment checks.
10. Keep GitHub Pages as host.

# 1. Logo and favicon

The handover pack contains finished assets:

```text
assets/logo-mark.svg
assets/favicon.svg
assets/favicon-16x16.png
assets/favicon-32x32.png
assets/apple-touch-icon.png
assets/icon-192.png
assets/icon-512.png
assets/site.webmanifest
```

Copy them to:

```text
docs/assets/logo-mark.svg
docs/assets/favicon.svg
docs/assets/favicon-16x16.png
docs/assets/favicon-32x32.png
docs/assets/apple-touch-icon.png
docs/assets/icon-192.png
docs/assets/icon-512.png
docs/site.webmanifest
```

Replace:

```html
<span class="brand-mark" aria-hidden="true">🔎</span>
```

with:

```html
<span class="brand-mark" aria-hidden="true">
  <img src="assets/logo-mark.svg" alt="" width="48" height="48">
</span>
```

Add to `<head>`:

```html
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="assets/favicon-32x32.png" sizes="32x32" type="image/png">
<link rel="icon" href="assets/favicon-16x16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
```

Adjust CSS without changing header dimensions:

```css
.brand-mark {
  width: 48px;
  height: 48px;
  display: block;
  flex: 0 0 48px;
  background: transparent;
  border-radius: 0;
  box-shadow: none;
}
.brand-mark img { display: block; width: 100%; height: 100%; }
```

Acceptance:

- recognisable at 48 px and as 16/32 px favicon;
- no emoji remains;
- relative asset paths work at `/sentence-sense-detective/`;
- use the supplied SVG, not the earlier raster illustration with a generated background.

# 2. About: honest but not a methodology dashboard

Exercises, answer choices, feedback, summaries, and public question data must remain free of raw UD labels, relation names, remapping tables, confidence classes, and development jargon.

The About dialog is a narrow exception. Keep its current short product description and four-step scoring list, then add exactly this:

```html
<section class="about-project" aria-labelledby="about-project-title">
  <h3 id="about-project-title">How the question bank is built</h3>
  <!-- methodology-note:start -->
  <p>The English pilot began with 106 examples reviewed by an experienced grammar teacher. Behind the scenes, we are testing how sentences annotated automatically with Stanza and Universal Dependencies can be translated into the grammatical categories students actually use in class. Students do not need to learn UD labels: that technical layer belongs to corpus preparation, not to the learning task. The reviewed examples remain our reference set; larger automatically prepared batches are provisional until they are checked and corrected.</p>
  <!-- methodology-note:end -->

  <h3>Our aim</h3>
  <p>Our next target is an open corpus of roughly 10,000 annotated English sentences that can supply varied, randomly selected practice. The longer-term aim is a reusable multilingual tool for the languages taught at the Department of Translation and across the Faculty of Arts. The code and, wherever source licensing permits, the data will remain openly available on GitHub.</p>

  <p class="pilot-version">English pilot · version <span id="about-version"></span></p>
</section>
```

Populate `#about-version` from public metadata.

Update `AGENTS.md` and `scripts/validate_data.py`:

- keep the prohibition everywhere except the exact block between `methodology-note:start/end`;
- whitelist only that block rather than weakening the scan globally;
- raw dependency labels (`nsubj`, `obj`, `ccomp`, etc.) remain prohibited throughout `docs/`;
- no teacher comments, confidence values, source spreadsheets, internal rules, or private notes under `docs/`.

# 3. Corpus sentences and quiz questions are different entities

Model separately:

- **sentence**: source text, provenance, and annotations;
- **annotation unit**: a word, phrase, sentence element, or clause;
- **question**: one pedagogical prompt generated from one annotation unit.

One sentence may yield several questions. A 10,000-sentence corpus may therefore produce more than 10,000 questions.

Sample questions, not sentences, but never show the same `sentence_id` twice in one ten-question round.

# 4. Canonical file structure

Migrate from one giant `data/questions.json` toward:

```text
data/
  corpus/en/
    manifest.json
    sentences-0001.jsonl
    sentences-0002.jsonl
    ...
  questions/en/
    reviewed-core.jsonl
    provisional-0001.jsonl
    provisional-0002.jsonl
    ...
  sources/en-sources.json

schema/
  sentence.schema.json
  question.schema.json
  public-manifest.schema.json
  public-shard.schema.json

docs/data/en/
  manifest.json
  parts-of-speech/shard-0001.json
  sentence-elements/shard-0001.json
  clauses/shard-0001.json
  ...
```

Use JSONL for canonical records. Recommended source shard: 500 sentences. Recommended public shard: 250–500 questions and roughly 500 KB or less uncompressed. Do not create one file per sentence.

# 5. Sentence schema

Create a sentence contract broadly like:

```json
{
  "id": "en-s000001",
  "language": "en",
  "text": "Sarah and her daughters arrived first.",
  "source": {
    "source_id": "source-key",
    "document_id": "optional-document-key",
    "licence": "licence-value",
    "attribution": "required attribution"
  },
  "machine_annotation": {
    "engine": "stanza",
    "engine_version": "recorded-at-build-time",
    "model": "recorded-at-build-time",
    "payload": {}
  },
  "pedagogical_annotations": [],
  "review_status": "provisional"
}
```

Rules:

- stable unique IDs;
- UTF-8 text preserved exactly except logged normalisation;
- mandatory source and licence metadata;
- unknown/incompatible rights block deployment;
- machine annotation stays out of `docs/`;
- annotation spans use half-open Unicode character offsets `[start,end)`;
- discontinuous targets use multiple spans.

# 6. Question schema and migration

Internal question record:

```json
{
  "id": "en-q000001",
  "sentence_id": "en-s000001",
  "language": "en",
  "mode": "sentence-elements",
  "subskill": "Subject",
  "sentence": "Sarah and her daughters arrived first.",
  "target_spans": [{"start": 0, "end": 23}],
  "prompt": "What is the function of the highlighted phrase?",
  "answer": "S — Subject",
  "options": ["S — Subject", "DO — Direct Object", "SC — Subject Complement", "A — Adverbial"],
  "explanation": "Sarah and her daughters tells us who arrived, so the phrase functions as the subject.",
  "review_status": "teacher-reviewed"
}
```

Public shards contain only browser-required fields plus stable question/sentence IDs. Strip machine annotations, comments, reviewer identity, confidence, internal rules, and private notes.

Migrate all existing `targets: [{text, occurrence}]` to offsets. Add regression tests proving the visible highlighting remains unchanged for all 156 existing questions.

Change the language schema from `const: en` to a BCP-47-compatible string, while deploying only `en` now.

# 7. Pipeline stages

Implement independently testable scripts:

```text
scripts/ingest_sentences.py
scripts/preannotate_stanza.py
scripts/build_pedagogical_candidates.py
scripts/build_question_bank.py
scripts/build_public_shards.py
scripts/validate_corpus.py
scripts/validate_public_shards.py
```

## Ingestion

Accept UTF-8 TSV or JSONL. Minimum TSV columns:

```text
sentence_id	language	text	source_id	document_id	licence	attribution
```

Reject missing IDs/text/source/licence, duplicate IDs, and invalid records. Report exact and near duplicates separately. Preserve punctuation and emit an audit report.

## Machine pre-annotation

Stanza/UD is internal preparation only.

- record versions/models;
- never download models without approval;
- keep output canonical/internal, not public;
- do not claim automatic output is pedagogically correct.

## Candidate generation

- use the 106 reviewed cases as regression anchors;
- generate candidates for all three modes;
- mark automatic output `provisional`;
- send ambiguous/unsafe cases to a rejection/review queue rather than forcing them into the bank;
- use controlled explanation templates that refer to the actual target and function.

## Human correction

Do not build a public teacher dashboard. Provide review TSV/JSONL export, corrected-file ingestion, stable IDs, idempotent updates, change reports, and status transition from `provisional` to `teacher-reviewed`.

# 8. Public manifest and lazy shards

Replace `window.SENTENCE_SENSE_DATA` as the large-bank delivery mechanism.

Generate `docs/data/en/manifest.json` with computed totals, modes, shard paths, counts, hashes, and version. Example:

```json
{
  "title": "Sentence Sense Detective",
  "language": "en",
  "version": "0.3.0",
  "round_size": 10,
  "totals": {"sentences": 10000, "questions": 18420, "teacher_reviewed": 106, "provisional": 18314},
  "shards": [
    {"id": "en-pos-0001", "mode": "parts-of-speech", "path": "parts-of-speech/shard-0001.json", "count": 400, "sha256": "..."}
  ]
}
```

Initial page load fetches the manifest only. A question shard is fetched only after the student selects a mode.

Round algorithm:

1. filter shards by mode;
2. choose a shard with probability proportional to count;
3. fetch it;
4. sample ten unique questions;
5. reject duplicate question IDs and duplicate `sentence_id` values;
6. avoid recently seen questions where possible;
7. if fewer than ten remain, fetch one more weighted shard;
8. preserve current option shuffling, scoring, retry, reveal, summary, and review logic.

Store at most 500 recent question IDs per mode. Avoidance is best-effort and may never block a round.

Provide accessible Loading, Retry, and Return home states for fetch failure.

# 9. Keep the reviewed core visible

Do not statistically bury the 106 reviewed questions under a much larger provisional bank.

Add a configurable sampling policy, for example:

```json
{"reviewed_core_share": 0.2}
```

Target roughly two reviewed-core questions in a ten-question round when the selected mode has reviewed items. Do not show “gold” or review-status badges in the quiz UI.

# 10. Report-question link

Add near the feedback/explanation area:

`Something wrong with this question? Report it.`

Open a prefilled GitHub issue containing only stable question ID, mode, current page URL, and an empty suggested-correction field. Never include the student's answer, score, progress, or browser information. Add a content-correction issue template. Hide gracefully in forks/local previews without a configured issue URL.

# 11. Validation and tests

Preserve all scoring tests and add:

- logo and every favicon/manifest asset exist and are referenced;
- no emoji brand mark;
- About methodology block exists once and is the only permitted public location for `Stanza`, `Universal Dependencies`, and `UD`;
- no raw dependency relations in `docs/`;
- About version comes from metadata;
- unique sentence/question IDs;
- mandatory provenance/licence;
- valid Unicode spans;
- every question references an existing sentence;
- exactly four unique options and answer included;
- all 106 reviewed source IDs still represented exactly once;
- `Operator` remains separate;
- manifest totals equal shard totals;
- no duplicates across shards;
- hashes match files;
- no internal fields leak;
- deterministic build;
- ten unique questions and ten unique sentence IDs per round;
- selected mode only;
- reviewed-core policy within statistical tolerance;
- bounded recent history;
- fetch failure is recoverable;
- initial load does not fetch all shards.

Do not install a browser framework without approval. Prefer pure functions and existing tooling, plus a documented manual browser audit if necessary.

# 12. Performance budgets

- manifest only on initial data load;
- public shards target ≤500 KB uncompressed;
- fail CI at >1 MB per shard;
- fail CI at >250 KB manifest;
- fail CI if `docs/` exceeds 250 MB at this stage;
- report site size, largest shard, sentence count, question count, reviewed count, and provisional count in CI;
- retain only current/review questions, one or two fetched shards, and bounded history in memory/storage.

# 13. Source-rights stop condition

Codex must not scrape, invent, generate, or silently choose the 10,000 source sentences.

The project team must supply the corpus and confirm its licence/publication status. Until then:

- implement and test the scalable architecture;
- migrate the existing 156 questions;
- use only a small checked fixture;
- produce a dry-run report for a hypothetical 10,000-sentence input;
- stop before fabricating or publishing unlicensed text.

# 14. Documentation

Update README, AGENTS.md, CODEX_HANDOVER.md, CHANGELOG.md, schemas, citation metadata if present, and licence/attribution docs. Clearly separate code licence, pedagogical annotations, and source-sentence rights.

# 15. GitHub Pages

Keep the existing Actions deployment from `docs/`. Do not move to a backend. A custom domain may be added later while retaining GitHub Pages, but do not change Pages settings or add a CNAME without instruction.

# 16. Required order

1. Branch and baseline tests.
2. Logo/favicon integration.
3. About copy plus narrow validator exception.
4. Offset schemas and migration of current 156 questions.
5. JSONL corpus/question structure and deterministic shard builder.
6. Manifest/lazy loader and no-repeat logic.
7. Report-question link.
8. Tests and docs.
9. Desktop 1440×900, mobile 390×844, keyboard-only, reduced-motion, all scoring paths.
10. Completion report: changed files, tests, before/after load behaviour, counts, site/shard sizes, and blockers.
11. Stop before push/deploy unless explicitly approved.

# 17. Acceptance criteria

Complete only when:

- supplied vector logo and all favicon variants are live;
- About honestly explains Stanza/UD, human review, 10,000-sentence aim, multilingual expansion, and GitHub openness;
- technical labels do not leak into exercises;
- all existing 156 questions work unchanged in learning behaviour;
- all 106 reviewed cases remain protected;
- page loads a manifest first and shards only on mode selection;
- no round repeats a question or source sentence;
- a licensed 10,000-sentence input can be ingested without front-end changes;
- public shards contain no internal payload/comments;
- performance budgets pass;
- GitHub Pages remains deployable under the project subpath;
- no corpus is fabricated or published without rights approval.

## Suggested Codex prompt

```text
Read AGENTS.md, CODEX_HANDOVER.md, and CODEX_HANDOVER_10K_OPEN_CORPUS.md in full. Treat the 10K handover as the newest authoritative brief. Preserve the existing Sentence Sense Detective interface, scoring, and 106 reviewed cases. Integrate the supplied vector logo and complete favicon set; add the exact honest About methodology/aim section; migrate targets to character offsets; and replace the monolithic question payload with a deterministic manifest-and-shards architecture suitable for roughly 10,000 annotated sentences. Keep technical annotation details out of exercises and allow them only in the explicitly whitelisted About block. Build and test the scalable ingestion pipeline, but do not source or fabricate the 10,000 sentences. Do not install, push, or deploy without explicit approval. Report all tests, data counts, site size, and shard size.
```
