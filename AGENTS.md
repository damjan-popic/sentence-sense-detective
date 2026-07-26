# AGENTS.md — Sentence Sense Detective

These instructions apply to every Codex task in this repository.

## Product purpose

Sentence Sense Detective is a student-facing grammar practice tool. It is not a research demonstrator, annotation inspector, technical dashboard, or linguistic pipeline interface.

The public site must do one thing well: present a highlighted target, ask a clear grammar question, score the response, explain the answer, and support another short round.

## Locked product decisions

1. Product name: **Sentence Sense Detective**.
2. Current language: **English pilot**.
3. Public practice modes:
   - Parts of Speech;
   - Sentence Elements;
   - Clauses (advanced).
4. Answer interaction: **highlighted-target mode only**. Do not add span selection in this scaffold.
5. Round length: **10 questions** unless a review round contains fewer mistakes.
6. Scoring:
   - first-attempt correct = 1 point;
   - retry correct = 0 points;
   - reveal = 0 points;
   - no negative points;
   - streak = consecutive first-attempt correct answers.
7. One retry follows an incorrect first attempt.
8. Every round ends with:
   - score;
   - first-try percentage;
   - subskill breakdown;
   - missed-item explanations;
   - Review mistakes action.
9. Progress remains in browser storage only.
10. No login, backend, analytics, tracking, leaderboard, social sharing, advertising, or paid service.
11. `Operator` is a separate sentence-element answer category.

## Content boundaries

The deployed `docs/` directory must not expose research-pipeline terminology or implementation metadata. In particular, do not show or explain:

- parser internals;
- annotation-system names;
- source-analysis cues;
- technical transformation categories;
- teacher-review workflow labels;
- internal status fields;
- private comments;
- source spreadsheet columns.

Do not add a methodology dashboard or a reference table of internal analyses.

Public wording must remain about grammar learning: words, sentence elements, clauses, answers, explanations, scores, and practice.

## Data rules

- `data/questions.json` is the canonical learning dataset.
- `docs/data/questions.js` is generated from the canonical dataset.
- All **106 teacher-reviewed source cases** must remain represented exactly once among the reviewed Sentence Elements and Clauses questions.
- The **50 parts-of-speech questions** are a provisional scaffold built from sentences in the same source set. They may be corrected after deployment, but changes must be documented in `CHANGELOG.md`.
- Do not silently replace a reviewed answer. Add a regression test and explain the correction in `CHANGELOG.md`.
- Public questions must contain exactly four unique options, including the correct answer.
- Every target must occur in the displayed sentence.
- Source IDs and internal status may exist in data for maintenance, but the UI must not display them.

## Interface rules

- Keep the current warm, compact visual direction: friendly but suitable for university students.
- Preserve keyboard access and visible focus states.
- Preserve reduced-motion support.
- Maintain a usable layout at 320 px and above.
- Avoid external fonts, trackers, CDNs, and runtime dependencies.
- Keep the site static and deployable from `docs/`.
- Prefer small, readable vanilla JavaScript over a framework migration.

## Required checks

Run all of these before completing work:

```bash
python scripts/build_public_data.py --check
python scripts/validate_data.py
python -m unittest discover -s tests -v
node --check docs/assets/app.js
```

For layout changes, also serve the site and inspect desktop and mobile widths:

```bash
python -m http.server 8000 --directory docs
```

## GitHub Pages

The workflow in `.github/workflows/pages.yml` is the deployment path. Do not publish to a remote repository until the owner, repository name, visibility, and rights status are confirmed.
