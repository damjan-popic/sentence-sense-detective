# Codex handover — Sentence Sense Detective scaffold

## 1. Locked brief

The following decisions are final for this scaffold:

- **Title:** Sentence Sense Detective
- **Language:** English pilot
- **Modes:**
  1. Parts of Speech
  2. Sentence Elements
  3. Clauses (advanced)
- **Interaction:** highlighted target only
- **Round size:** 10
- **Scoring:**
  - 1 point only for a correct first attempt;
  - one learning retry after an incorrect answer;
  - retry and reveal are worth 0;
  - no negative points;
  - streak counts consecutive first-attempt correct answers.
- **End-of-round output:** score, percentage, subskill breakdown, mistakes, and a review-mistakes round.
- **Storage:** browser-local progress only.
- **Operator:** a separate answer category.
- **Source policy:** use the current 106 reviewed cases now; do not request another instructor pass before the first deployment.
- **POS policy:** use the provisional POS bank built from the same source sentences; make qualitative corrections after deployment.

## 2. What already exists

The repository already contains a working static scaffold:

- 156 questions in total;
- 106 reviewed source cases represented exactly once;
- 50 provisional POS questions;
- a three-mode home screen;
- highlighted-target questions;
- first-attempt scoring, one retry, reveal, streaks, summary, and mistake review;
- local progress storage;
- responsive CSS;
- data validation and regression tests;
- GitHub Pages workflow.

This is an audit-and-polish task, not permission to reintroduce the previous technical interface.

## 3. Non-negotiable public boundary

Nothing in the student-facing site may discuss the machinery used to prepare the examples. Do not show technical labels, source-analysis cues, automaticity classes, implementation rules, private review comments, or research terminology.

The public site should read like a small grammar-learning product, not a paper appendix.

A test scans the entire `docs/` directory for prohibited research-pipeline language. Keep that test.

## 4. Data responsibilities

Canonical file: `data/questions.json`

Generated browser copy: `docs/data/questions.js`

Private notes: `internal/teacher_notes.json`

The private notes must never be imported by, copied into, or exposed from `docs/`.

The 106 reviewed IDs must remain exact and complete. The current transform deliberately makes two pedagogical choices:

- in `SE-P-02`, the visible target is **Did** and the answer is **Operator**;
- `REVIEW-01` becomes a scored linguistic ambiguity question with **Context needed** as the answer.

Do not undo those choices without an explicit instruction.

## 5. Codex tasks, in order

### Task A — verify the current implementation

Run:

```bash
python scripts/build_public_data.py --check
python scripts/validate_data.py
python -m unittest discover -s tests -v
node --check docs/assets/app.js
```

Fix failures before visual work.

### Task B — browser audit

Serve `docs/` locally and test at minimum:

- 1440 × 900;
- 390 × 844;
- keyboard-only navigation;
- reduced-motion mode;
- a complete round in every mode;
- first-answer correct;
- first-answer wrong then retry correct;
- two wrong answers;
- Show answer;
- perfect round with no review button;
- review-mistakes round;
- browser refresh after saved progress;
- reset progress.

### Task C — content audit

Check every question for:

- exact target highlighting;
- four unique answer options;
- answer present in options;
- plain-English prompt;
- explanation that teaches the grammar point;
- no leaked internal language;
- no obviously absurd distractor.

Do not “improve” reviewed answers from general intuition. Record any suspected issue in `CONTENT_REVIEW_NOTES.md` instead.

### Task D — polish without feature creep

Allowed:

- accessibility fixes;
- mobile layout fixes;
- clearer microcopy;
- better focus behaviour;
- minor visual refinement;
- test coverage;
- deployment hardening.

Not allowed:

- span selection;
- accounts;
- backend;
- AI chat;
- arbitrary sentence input;
- teacher dashboard;
- leaderboard;
- analytics;
- framework rewrite;
- technical methodology page;
- exposing private notes;
- replacing the 10-question round model.

### Task E — deployment readiness

Keep the site deployable by GitHub Actions from `docs/`. Do not create or publish a remote repository until the repository owner, final name, visibility, and publication rights are explicitly confirmed.

## 6. Acceptance criteria

The task is complete only when:

1. all required checks pass;
2. the site works at desktop and mobile widths;
3. all three practice modes complete a round correctly;
4. the score never exceeds the number of first-attempt correct answers;
5. a retry never awards a point;
6. Show answer never awards a point;
7. a first mistake breaks the streak;
8. mistake review contains every non-first-try item exactly once;
9. all 106 reviewed source IDs remain represented exactly once;
10. `Operator` remains independently selectable;
11. no private notes appear under `docs/`;
12. no prohibited technical terminology appears in the public site;
13. the GitHub Pages workflow validates before deployment.

## 7. Suggested Codex prompt

```text
Read AGENTS.md and CODEX_HANDOVER.md in full. Treat the locked brief as authoritative. Run every required check, audit the current Sentence Sense Detective scaffold in a browser at desktop and mobile widths, and fix only issues that improve correctness, accessibility, clarity, or deployment readiness. Do not add new product features, do not alter reviewed answers without documenting the issue and adding a regression test, and do not expose any private development metadata in docs/.
```
