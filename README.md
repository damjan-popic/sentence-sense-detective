# Sentence Sense Detective

**Spot it. Name it. Make it stick.**

Sentence Sense Detective is a small, dependency-free grammar practice site for an English pilot. Students complete ten-question rounds in three modes:

- **Parts of Speech** — 50 provisional scaffold questions;
- **Sentence Elements** — 44 teacher-reviewed questions;
- **Clauses** — 62 teacher-reviewed advanced questions covering clause type, marker, structure, and function.

The 106 reviewed cases all come from the current instructor-reviewed source set. The parts-of-speech bank uses sentences from that same set and is deliberately marked as provisional in the internal data so it can be improved after the first classroom deployment.

## Student experience

- The target word, phrase, or clause is already highlighted.
- A correct answer on the first attempt earns **1 point**.
- After an incorrect answer, the student gets **one learning retry**, worth no point.
- Revealing the answer earns no point.
- There are no negative points.
- A streak counts consecutive first-attempt correct answers.
- Every round ends with a score, percentage, category breakdown, and a **Review mistakes** round.
- Progress is stored only in the browser. There is no login, server, leaderboard, analytics, or tracking.

`Operator` is a separate answer category in the sentence-elements mode.

## Run locally

```bash
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000`.

## Validate

```bash
python scripts/build_public_data.py --check
python scripts/validate_data.py
python -m unittest discover -s tests -v
node --check docs/assets/round-state.js
node --check docs/assets/app.js
node --test tests/test_round_state.js
```

## Repository layout

```text
data/questions.json             canonical question bank
docs/                           static GitHub Pages site
docs/data/questions.js          browser-ready copy of the question bank
docs/assets/round-state.js       testable scoring state transitions
schema/question.schema.json      public question contract
scripts/build_public_data.py     refreshes docs/data from data/questions.json
scripts/validate_data.py         content and deployment checks
tests/                           regression tests
AGENTS.md                        persistent instructions for Codex
CODEX_HANDOVER.md                locked product brief and acceptance criteria
```

## Deploy with GitHub Pages

Push the repository to GitHub, then set **Settings → Pages → Source** to **GitHub Actions**. The included workflow validates the data and deploys the `docs/` directory.

No remote repository is created automatically. Repository ownership, public/private status, and the final repository name must be confirmed before publication.

## Multilingual direction

English is the first profile. The question schema already carries a language code, and additional languages can use the same interaction model while supplying their own reviewed terminology, examples, answer sets, and explanations.

## Licensing

Code and educational content are separated provisionally:

- code: `LICENSE-CODE`;
- question content and explanations: `LICENSE-CONTENT`.

Confirm the right to publish all source examples before making the repository public.
