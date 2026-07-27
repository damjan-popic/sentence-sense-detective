# Formal pedagogical remapping implementation

## Authority and preservation

- Canonical imported contract: `data/remap/en/martin_contract_106.json`.
- Source workbook SHA-256:
  `f62fcfcdc35d43d8425b63266b86ae54c3bd688d37ca5e47e0dab432f767a51d`.
- Contract JSON SHA-256:
  `6b3be571df252b662e2df5f0f4ea8063714f71535728fccc878f35f056dc2e4f`.
- Contract cases: 106 unique IDs.
- Decision inventory: 26 `OK`, 60 `Rule-based OK`, and 20
  `Needs manual review`.
- Martin-reviewed gold answers, IDs, terminology, and target spans changed: 0.
- Internal Slovene review fields exposed publicly: 0.

The prior 34,858-question heuristic bank from commit `a1ed4bd` is preserved
unchanged under `data/generated/legacy_handcoded_a1ed4bd/`. It is comparison
evidence only, never a formal-remap or public-build input.

## Architecture

1. JSON-compatible YAML files under `config/remap/en/` are the versioned rule
   source.
2. `scripts/compile_remap_rules.py` validates and compiles the profile, checks
   controlled labels, verifies complete contract coverage, and prevents any
   manual-review case from publishing.
3. `scripts/formal_remap_engine.py` applies the compiled rules to structural
   graph-match events and resolves incompatible same-target matches by
   downgrading them to review.
4. `scripts/remap_stanza_annotations.py` materialises formal results before
   question generation.
5. `scripts/generate_questions.py` performs presentation only: prompts,
   distractors, explanations, stable IDs, and the maximum two word-class
   presentations per sentence.

The presentation generator does not import the structural matcher or formal
engine and contains no direct UD-relation-to-pedagogical-label mappings.
The expanded remap and generated-question JSONL banks are stored as
deterministic `.jsonl.gz` streams; their decompressed canonical content remains
byte-identical across rebuilds while each repository blob stays below GitHub's
per-file limit.

Every internal candidate records the profile and profile hash, formal rule,
decision class, action, source case IDs, matched token/relation/POS evidence,
Stanza version, and model-bundle hash. Parts of Speech is isolated in the
explicit provisional `POS-PROFILE-EN-1.0.0` profile.

## Gold replay

- Pinned Stanza version: 1.14.0.
- Unique fixture sentences: 91.
- Cases replayed: 106.
- Exact label/span/action matches: 106.
- Parser, label, span, or action mismatches: 0.
- Manual-review cases auto-published: 0.

The zero-marker case remains an explicit non-highlightable review guard; no
synthetic `∅` is inserted into source text.

Four supplied comments have unrecoverable referents and are recorded as such,
not guessed: `SE-SC-05`, `CL-MARK-01`, `CL-STR-01`, and `CL-FUNC-01`. Their
dispositions are in `reports/remap_contract_coverage.*`.

## 10K execution and review

The existing selected corpus and pinned Stanza annotations are retained. The
formal materialisation, generated presentation bank, per-rule distribution,
old-versus-new impact categories, full review workbook, and stratified
review-only sample are reported in:

- `data/remap/en/remap_10k_report.json`;
- `data/generated/generation_report.json`;
- `reports/remap_rule_distribution.*`;
- `reports/remap_old_vs_new.*`;
- `data/review/review_pack.xlsx`;
- `reports/remap_manual_review_sample.xlsx`.

## Public selection and publication boundary

Only publish actions enter generated public shards. Review and conflict
downgrade outputs remain visible internally. Public rounds preserve reviewed
sampling and recent-history avoidance while sampling across available answers
and subskills; an answer label is capped at three per ordinary ten-question
round when alternatives exist.

`make remap-all` rebuilds and validates the formal pipeline locally. It does
not push or deploy; publication is a separate action requiring explicit
approval after report review.
