# Sentence Sense Detective — Codex handover for the 10,000-sentence English corpus

## 0. Authority and scope

Read, in this order:

1. `AGENTS.md`
2. the repository's existing `CODEX_HANDOVER.md`
3. this file

For this task, this file is the newest authoritative brief where it conflicts with older handovers. Preserve the existing student experience, scoring, visual character, 106 Martin-reviewed cases, and the separate `Operator` category.

Do not turn the public site into a parser, treebank, remapping, or annotation interface. Technical information may appear only in the narrowly defined **How the question bank is built** section of the About dialog.

Do not push or deploy until the local pipeline, tests, corpus report, and a browser preview have been shown to Damjan.

---

## 1. Locked product decisions

- Product title: **Sentence Sense Detective**.
- Public modes: **Parts of Speech**, **Sentence Elements**, and **Clauses**.
- Interaction: highlighted-target multiple choice.
- Round size: 10.
- Correct first attempt: 1 point.
- One unscored learning retry after a wrong answer.
- Show answer: 0 points.
- No negative points.
- `Operator` remains a separate sentence-element category.
- Progress remains local to the browser.
- No login, analytics, tracking, advertising, leaderboard, or backend.
- The static site must continue to deploy from `docs/` on GitHub Pages.

---

## 2. Corpus decision

### Primary source: MASC 3.0.0

Use the **Manually Annotated Sub-Corpus (MASC) 3.0.0** as the first source. It is a balanced corpus of approximately 500,000 words across 19 genres, distributed for any purpose under CC BY 3.0 US. Its sentence boundaries, tokens, lemmas, POS tags, chunks, and Penn Treebank syntax have been manually produced or validated. We will nevertheless run the project's own pinned Stanza pipeline so that the generated data follows one repeatable processing path and can later be reused for other languages.

Official information and download page:

- https://anc.org/data/masc/
- https://anc.org/data/masc/downloads/data-download/

Prefer the **data-only UTF-8 archive** for ingestion. The full annotation archive may also be downloaded for comparison and quality checks, but it is not required to generate the first public question bank.

### Fallback source: written OANC

If fewer than 10,000 sentences survive filtering and yield at least one usable question, fill the deficit from the **written portion of the Open American National Corpus (OANC)**. OANC contains about 15 million words overall, including about 11.4 million written words, and is unrestricted for use and redistribution, including commercial development.

Official information and download page:

- https://anc.org/data/oanc/
- https://anc.org/data/oanc/download/

Do not commit the complete OANC archive or its unpacked directory. The official archive is hundreds of megabytes and expands to several gigabytes. Keep external source downloads under a gitignored cache and commit only the selected 10,000-sentence derivative, provenance, question data, scripts, and reports.

### Why not use AMALGUM or UD English EWT as the main public source?

AMALGUM is technically excellent and may be added later, but its underlying source texts carry several different licences, including share-alike and non-commercial terms for some genres. UD English EWT has strong syntactic annotation but explicitly distinguishes the CC licence on its annotations from the mixed rights in the underlying web texts. MASC/OANC gives this project the cleanest first release for an open site and a possible printed companion.

### English variety

MASC/OANC is contemporary American English. Record `variety: "en-US"` in internal provenance. Do not generate questions whose answer depends on US/UK spelling or disputed regional usage. The existing 106 cases remain part of the English pilot and are not relabelled by variety. Later corpora may add British and other English profiles.

---

## 3. Required repository architecture

Keep the static site dependency-free. Add a separate local corpus-building toolchain.

Recommended layout:

```text
sentence-sense-detective/
├── AGENTS.md
├── CODEX_HANDOVER.md
├── CODEX_HANDOVER_MASC_OANC_10K.md
├── requirements-corpus.txt
├── Makefile
├── config/
│   ├── corpus_10k.yaml
│   ├── pedagogical_tagset_en.json
│   └── source_manifest.json
├── data/
│   ├── questions.json                         # existing canonical 156-question source, retained
│   ├── gold/                                  # immutable copy/index of the 106 reviewed cases
│   ├── corpus/
│   │   ├── sentences_10k.jsonl               # selected source sentences + provenance
│   │   └── sentences_10k.conllu              # pinned Stanza output
│   ├── generated/
│   │   ├── question_candidates.jsonl
│   │   ├── accepted_questions.jsonl
│   │   ├── rejected_questions.jsonl
│   │   └── generation_report.json
│   └── review/
│       ├── review_pack.xlsx
│       └── corrections/                      # imported human corrections
├── external/                                  # gitignored corpus downloads and extraction
├── docs/
│   ├── index.html
│   ├── credits.html
│   ├── assets/
│   └── data/
│       ├── manifest.json
│       ├── gold.json
│       └── shards/
├── scripts/
│   ├── corpus_pipeline.py
│   ├── fetch_corpus.py
│   ├── extract_masc.py
│   ├── select_sentences.py
│   ├── annotate_stanza.py
│   ├── generate_questions.py
│   ├── export_review_pack.py
│   ├── import_review_corrections.py
│   ├── build_public_shards.py
│   └── validate_data.py
├── reports/
│   ├── corpus_audit.md
│   ├── selection_report.json
│   ├── annotation_report.json
│   ├── question_generation_report.md
│   └── public_build_report.md
└── tests/
```

`external/`, downloaded archives, extracted full corpora, Stanza model files, caches, and temporary data must be ignored by Git.

---

## 4. Reproducible local environment

The user uses Python virtual environments, never Conda.

- Keep the existing site dependency-free.
- Put corpus-only dependencies in `requirements-corpus.txt`.
- Use a normal `.venv`.
- Pin every tested Python package version after the first successful run.
- Pin and record the Stanza package version, English model package identifier/version, download date, and SHA-256 where available.
- Respect an existing global Stanza cache; do not create a project-local copy of the same models unless explicitly requested.
- Use GPU when Stanza supports it and CUDA is available, with a transparent CPU fallback.
- Make every stage resumable and deterministic.
- Use a fixed default seed: `20260726`.

Required top-level commands:

```bash
make corpus-fetch
make corpus-audit
make corpus-select
make corpus-annotate
make corpus-generate
make corpus-review-pack
make corpus-build-public
make validate
make preview
```

Also provide a single resumable command:

```bash
make corpus-all
```

No stage may silently redownload, overwrite reviewed data, or change the selected 10,000 sentences without producing a diff and a new corpus version.

---

## 5. Source acquisition and provenance

### Download policy

1. Download from the official ANC/MASC site only.
2. Save the original archive unchanged under `external/downloads/`.
3. Record:
   - source page;
   - resolved download URL;
   - UTC retrieval time;
   - file size;
   - SHA-256;
   - corpus/version;
   - licence and attribution text.
4. Extract to `external/masc-3.0.0/`.
5. If MASC does not provide 10,000 accepted items, download and extract OANC under `external/oanc/` and select only written data.
6. Never scrape fresh web pages to replace the corpus.

### Per-sentence provenance

Every selected sentence must contain at least:

```json
{
  "sentence_id": "masc-blog-document-slug-s0001",
  "text": "…",
  "language": "en",
  "variety": "en-US",
  "source": {
    "corpus": "MASC",
    "corpus_version": "3.0.0",
    "document_id": "…",
    "genre": "blog",
    "source_path": "…",
    "licence": "CC BY 3.0 US",
    "attribution": "Open American National Corpus / MASC",
    "sentence_index": 1
  },
  "selection": {
    "seed": 20260726,
    "difficulty": "intermediate",
    "filter_version": "1.0.0"
  }
}
```

For an OANC fallback item, record OANC as the corpus and retain its original collection/domain identifiers.

Create `THIRD_PARTY_NOTICES.md`, `docs/credits.html`, and machine-readable `config/source_manifest.json`. The public question payload need not show provenance on every quiz screen, but the credits page must make the origin and licence clear.

---

## 6. Selection target: exactly 10,000 accepted sentences

A sentence is accepted only if it yields at least one structurally valid question candidate after annotation. The final corpus must contain exactly 10,000 unique sentence IDs and 10,000 unique normalized sentence texts.

### Initial MASC genre plan

Exclude spam in the first release. Also exclude Twitter and jokes initially unless the clean written/spoken pool cannot reach 10,000 after filtering.

Soft targets:

- 700 each from 12 written genres:
  - blog
  - email
  - essay
  - fiction
  - ficlets
  - government documents
  - journal
  - letters
  - newspaper
  - non-fiction
  - technical
  - travel guides
- 400 each from 4 dialogic genres:
  - court transcript
  - debate transcript
  - spoken
  - movie script

This totals 10,000. Targets are soft, not an excuse to accept bad material. If a genre falls short, redistribute within the same broad stratum first, then across the corpus. Report every redistribution.

### Document cap

- Default maximum: 75 accepted sentences from a single source document.
- No document may contribute more than 1% of the corpus.
- Deduplicate exact and near-duplicate text across documents.

### Mandatory filters

Reject or quarantine sentences that contain any of the following:

- fewer than 5 or more than 40 lexical tokens;
- no finite verb, unless the sentence is retained exclusively for an unambiguous POS question;
- headings, table rows, captions, bibliographic fragments, list fragments, or navigation text;
- URLs, email addresses, phone numbers, file paths, code, markup, or formula-heavy text;
- more than 20% digits/symbols;
- broken encoding, unmatched brackets/quotation marks, or obvious sentence-splitting failure;
- all-caps text or excessive punctuation;
- duplicate or near-duplicate text;
- text requiring unavailable document context to be intelligible;
- personally identifying private data;
- explicit sexual content, graphic violence, slurs, targeted harassment, or other material unsuitable for a general university learning tool.

Do not rewrite source sentences to make them cleaner. Reject and replace them. Preserve original punctuation and casing for accepted items.

### Difficulty distribution

Use token count, finite-clause count, dependency depth, and construction type—not length alone.

Target distribution:

- basic: 35%
- intermediate: 45%
- advanced: 20%

Report actual distributions by genre, length, clause count, and difficulty.

---

## 7. Stanza annotation

Run a local English Stanza pipeline with at least:

```text
tokenize,mwt,pos,lemma,depparse
```

Requirements:

- process documents in batches while preserving sentence/document provenance;
- output one canonical CoNLL-U file and one JSONL sentence record;
- include character offsets for every token;
- log parser/model versions and hardware used;
- make the run resumable by document;
- do not call remote APIs or LLM services;
- never expose raw UD/Stanza labels in the student exercise UI.

Where MASC annotations are available, use them as an independent comparison signal in the audit report. Do not silently replace the project's Stanza output with MASC annotations.

---

## 8. Question generation

### General rule

The 10,000 sentences are the corpus. Questions are derived learning items. One sentence may produce more than one candidate, but a public round must never show the same source sentence twice.

Every accepted sentence must yield at least one question. Generate all high-confidence candidates, but designate one `primary_question_id` per sentence so the first build can guarantee broad sentence coverage.

### Controlled vocabulary

Extract the current public answer inventory from the existing 156 questions and store it in `config/pedagogical_tagset_en.json`. Do not invent a new student-facing label during automated generation. A new label requires an explicit data migration and human approval.

`Operator` is a separate category and must remain so.

### Parts of Speech

Generate only contextually safe candidates. Use the existing pedagogical labels, not raw parser labels. Examples include:

- proper noun;
- noun;
- pronoun;
- determiner;
- adjective;
- adverb;
- lexical verb;
- auxiliary verb;
- modal auxiliary;
- preposition;
- coordinator;
- subordinator;
- particle;
- numeral;
- interjection, if already present in the controlled vocabulary.

Apply explicit lexical/context rules where the automatic category alone is insufficient—for example modal versus non-modal auxiliary, determiner versus pronoun, particle versus preposition, and infinitival `to` versus preposition. Skip ambiguous candidates rather than manufacturing certainty.

### Sentence Elements

Generate only candidates supported by strong structural evidence and the Martin-reviewed reference cases. Candidate labels may include:

- S
- P
- Operator
- DO
- IO
- SC
- OC
- A

Direct-looking parser relations are not automatically pedagogical truth. Use guards for:

- expletive/formal subjects;
- copular versus linking-verb complements;
- object complements;
- prepositional complements versus adverbials;
- duration NPs;
- complex and split predicators;
- reduced and non-finite clauses;
- clause-level sentence elements.

Only high-confidence candidates enter the default public bank. Lower-confidence candidates go to the review pack with reasons.

### Clauses

Generate candidates for the dimensions already represented in the reviewed bank:

- clause class/type;
- marker type;
- structure;
- function.

Use strict guards for nominal relatives/free relatives, zero relatives, reduced clauses, supplementive clauses, purpose/result, restrictive/non-restrictive relatives, appositive clauses, and clauses functioning as postmodifiers. Do not infer punctuation-dependent distinctions when punctuation is absent or unreliable.

### Internal statuses

Use explicit internal statuses such as:

- `martin-reviewed`
- `auto-high-confidence`
- `human-reviewed`
- `needs-review`
- `rejected`

The statuses must never appear in the quiz UI. The About section may truthfully explain that most of the expanded bank is automatically prepared and corrected over time.

### Distractors and explanations

- exactly four unique answer options;
- correct answer included;
- distractors drawn from the same pedagogical dimension and difficulty band;
- avoid obviously absurd distractors;
- explanations must describe the grammar, not the parser;
- generate explanations from controlled templates, not an LLM;
- every target uses character offsets, not substring occurrence guessing;
- target offsets must align exactly with the displayed sentence.

---

## 9. Preserve the 106 reviewed cases

The existing 106 Martin-reviewed Sentence Elements and Clauses cases are immutable reference items unless Martin or Damjan explicitly approves a correction.

- Keep every reviewed ID represented exactly once.
- Add regression tests for their sentence, target offsets, answer, and explanation.
- Keep the existing 50 POS scaffold items for now, but allow them to be superseded only through a documented migration.
- Store the 106 cases in a dedicated gold/reference index.
- Configure the round sampler so that reviewed items remain visible after expansion. Default reviewed-item weight: 15% of ordinary rounds, configurable in the manifest.

---

## 10. Human review workflow

Create `data/review/review_pack.xlsx` with one row per generated question candidate and these columns:

- question ID
- sentence ID
- genre
- sentence
- highlighted target
- mode
- subskill
- proposed answer
- four options
- explanation
- confidence
- rule ID
- accept / correct / reject
- corrected target
- corrected answer
- corrected explanation
- reviewer
- review date
- note

Use dropdown validation for the decision column. Provide a deterministic importer that:

- validates IDs and target offsets;
- refuses conflicting duplicate reviews;
- records reviewer/date/source file;
- writes a change log;
- never overwrites Martin-reviewed cases silently.

Add a discreet **Report this question** link after feedback. It should open a prefilled GitHub issue containing the question ID, mode, sentence, highlighted target, displayed answer, app version, and a blank field for the report. Do not collect anything automatically.

---

## 11. Public data delivery: manifest + shards

Remove the initial-page dependency on one monolithic `questions.js` containing the entire bank.

Create:

```text
docs/data/manifest.json
docs/data/gold.json
docs/data/shards/pos-000.json
docs/data/shards/pos-001.json
...
docs/data/shards/se-000.json
...
docs/data/shards/clause-000.json
...
```

Recommended shard size: 250–500 questions.

The manifest must include:

- corpus/question-bank version;
- build timestamp;
- total sentence count;
- total question count;
- counts by mode, subskill, difficulty, source corpus, and review status (status counts may be omitted from student UI);
- each shard path, count, byte size, SHA-256, mode, and difficulty coverage;
- round size;
- reviewed-item sampling weight.

At mode start:

1. load the small manifest;
2. choose shards using `crypto.getRandomValues`;
3. fetch only enough shards to assemble a round;
4. select 10 unique question IDs and 10 unique sentence IDs;
5. avoid recently seen IDs from a bounded local history;
6. respect mode and difficulty distribution;
7. shuffle answer options;
8. fail gracefully and retry another shard if a fetch fails.

Bound local history to at most 250 question IDs and 150 sentence IDs per mode. Do not turn local storage into a copy of the corpus.

The full 10,000-sentence source corpus and CoNLL-U may be packaged as a versioned release artifact rather than loaded by the browser. The website should publish only what it needs for practice plus an open, documented download path.

---

## 12. About dialog and authors

Replace the current short About copy with the exact content in `ABOUT_COPY_EN.md` supplied with this handover.

Required sections:

1. About Sentence Sense Detective
2. How the question bank is built
3. Our aim
4. About the authors
5. Sources, openness, and privacy

The **How the question bank is built** section is the only public location permitted to name Stanza or Universal Dependencies. Do not use the word “remapping”. Do not show tags, rules, trees, confidence scores, review labels, or source spreadsheet terminology.

### Author links

- Martin Grad: https://www.ff.uni-lj.si/en/staff/martin-anton-grad
- Damjan Popič: https://www.ff.uni-lj.si/zaposleni/damjan-popic

Use proper external links with `rel="noopener noreferrer"`. Martin is the principal author and grammar lead. Damjan is the co-author and project lead.

Make the dialog usable on a 320-pixel screen:

- `max-height: min(86vh, 760px)`;
- internal scrolling;
- visible close button;
- logical heading hierarchy;
- keyboard focus kept within the native `<dialog>`;
- author cards stack on mobile;
- no author photos unless supplied later.

Add a quiet version line: `English pilot · Version {metadata.version}`.

---

## 13. Adjust the public-term validator narrowly

The current validator forbids `UD`, `Stanza`, `mapping`, `parser`, `provisional`, and related words everywhere under `docs/`. Do not simply delete this protection.

Implement a narrow allowlist:

```html
<!-- PUBLIC_METHODOLOGY_ALLOWLIST_START -->
<section id="about-methodology">…</section>
<!-- PUBLIC_METHODOLOGY_ALLOWLIST_END -->
```

Validation rules:

- the two markers must occur exactly once and only in `docs/index.html`;
- prohibited-term scanning removes only the text between those markers before scanning the remainder of `docs/`;
- the allowlisted block may contain only the approved About copy;
- it may mention `Stanza` and `Universal Dependencies`;
- it must not contain raw labels, parser output, technical rules, confidence values, `manual review`, `rule-based`, private comments, source IDs, or internal status names;
- add a test that inserts a prohibited term outside the block and proves validation fails.

The quiz itself, feedback, summary, mode cards, and question payload remain free of technical annotation terminology.

---

## 14. Logo and favicon

Integrate the supplied vector mark and complete favicon family.

Required files under `docs/assets/brand/`:

- `logo-mark.svg`
- `favicon.svg`
- `favicon-16x16.png`
- `favicon-32x32.png`
- `apple-touch-icon.png` (180×180)
- `icon-192.png`
- `icon-512.png`
- `site.webmanifest`

Replace the emoji in the header with the SVG logo. Add:

```html
<link rel="icon" href="assets/brand/favicon.svg" type="image/svg+xml">
<link rel="icon" href="assets/brand/favicon-32x32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="assets/brand/apple-touch-icon.png">
<link rel="manifest" href="assets/brand/site.webmanifest">
```

Do not embed the large AI-generated illustration as the header logo. Use the clean vector mark in this handover.

---

## 15. Tests and acceptance criteria

### Corpus tests

- exactly 10,000 accepted sentence records;
- all `sentence_id` values unique;
- all normalized texts unique;
- provenance and licence present for every record;
- no excluded corpus genre in the first build unless explicitly reported and approved;
- no document exceeds the configured cap;
- all filters produce counts by rejection reason;
- deterministic selection for seed `20260726`;
- rerunning with unchanged inputs produces byte-identical selected JSONL and question candidates.

### Annotation tests

- valid CoNLL-U;
- sentence/token character offsets align with source text;
- every sentence has recorded Stanza/model versions;
- failed documents can be resumed without reprocessing completed ones.

### Question tests

- all 106 reviewed cases preserved exactly once;
- every accepted corpus sentence has at least one accepted question;
- every question has exactly four unique options;
- answer is in options;
- target offsets align exactly;
- no raw technical labels in public prompt/answer/explanation;
- controlled vocabulary only;
- reviewed cases pass regression tests;
- no sentence repeats within a round.

### Public build tests

- manifest counts equal shard counts;
- shard hashes and byte sizes match;
- no shard exceeds the configured size budget;
- initial page loads without downloading all question shards;
- a round can be completed with network disabled after its required shards are loaded;
- recent-history avoidance works and remains bounded;
- report link is correctly prefilled;
- About copy and author links are present;
- logo and all favicon links return 200 locally;
- `site.webmanifest` validates;
- layout works at 320, 390, 768, and 1440 pixels;
- keyboard and reduced-motion behavior remain intact.

### Performance budget

After the 10,000-sentence build:

- initial HTML/CSS/JS/manifest transfer target: under 500 KB uncompressed, excluding optional images;
- no initial download of the full question bank;
- individual question shards target: under 500 KB uncompressed;
- no runtime framework or CDN.

---

## 16. Mandatory dry-run report before deployment

Codex must stop after local build and report:

- official source URL and archive SHA-256;
- source corpus/version/licence;
- raw document and sentence counts;
- rejection counts by reason and genre;
- whether OANC fallback was needed;
- accepted sentence counts by genre/difficulty/source;
- Stanza package/model versions and runtime;
- generated/accepted/review-needed/rejected question counts by mode and label;
- number and percentage of sentences with 1, 2, 3+ questions;
- total public site size;
- number and size range of shards;
- all test results;
- a random 100-question review sample as XLSX;
- screenshots of home, About, one quiz question, and summary on desktop and mobile.

Do not push or deploy until Damjan approves the report and sample.

---

## 17. Precise Codex execution prompt

```text
Read AGENTS.md, CODEX_HANDOVER.md, and CODEX_HANDOVER_MASC_OANC_10K.md in full. Treat the MASC/OANC handover as the newest authoritative brief. Preserve the existing Sentence Sense Detective interface, scoring, Operator category, and all 106 Martin-reviewed cases. First update the About dialog with the supplied exact copy and author links, integrate the supplied SVG logo and full favicon family, and implement the narrow methodology-term allowlist without weakening the rest of the public-content validator. Then build a reproducible, resumable local corpus pipeline that downloads MASC 3.0.0 from the official ANC site, audits it, selects exactly 10,000 unique pedagogically usable sentences with provenance and deterministic genre/difficulty balancing, and falls back only to the written OANC if MASC cannot meet the target after filtering. Run a pinned local Stanza English pipeline, generate conservative pedagogical question candidates using the existing controlled vocabulary and 106 reviewed cases as regression anchors, export a review workbook, and build a manifest-plus-shards public bank for GitHub Pages. Do not scrape new web text, call remote AI services, fabricate corpus sentences, expose technical labels in exercises, push, or deploy. Stop with the required dry-run report, tests, 100-question review sample, size report, and screenshots.
```
