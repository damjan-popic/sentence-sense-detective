# Browser audit — 0.3.0

Date: 2026-07-26
Local URL: `http://127.0.0.1:8000/`

## Layout and content

- Desktop 1440 × 900: home view, supplied vector logo, mode cards, progress section, and About dialog rendered without clipping or overlap.
- About dialog: exact methodology and aim copy visible; public version displayed as `0.3.0`.
- Mobile 390 × 844: Sentence Elements practice view remained usable and readable. Measured document/body scroll width was 375 px against a 390 px viewport, so no horizontal overflow was present.
- Parts of Speech, Sentence Elements, and Clauses each loaded a ten-question round from their mode shard.
- Browser request log showed the initial page load requested the manifest but no question shard. The first question shard was requested only after mode selection.

## Interaction and scoring

- Correct first answer: score changed from `0/10` to `1/10`; streak changed from `0` to `1`.
- Wrong first answer: score stayed unchanged; streak reset; one retry appeared.
- Correct retry: question finalized; score stayed unchanged.
- Two wrong answers: question finalized; correct answer and explanation appeared; score stayed unchanged.
- Show answer: question finalized; score stayed unchanged.
- Completed a ten-question Parts of Speech round: `1/10`, `10%` first-try accuracy, category breakdown, nine missed items.
- Review mistakes opened a nine-question review round containing the missed items.
- Progress persisted after opening a fresh page and showed `1 of 10 correct first time · 1 round · best streak 1`.
- Reset progress confirmation cleared the stored statistics.
- Keyboard shortcut `1` selected the first visible answer and advanced to the retry state.
- The correction link contained question ID, mode, page URL, and an empty suggested-correction field; it did not contain the learner’s answer, score, or progress.

## Accessibility and runtime

- Focus moved to the question card on round start and to the summary heading on completion.
- The mobile practice card retained semantic headings, fieldset/group labelling, progressbar semantics, and visible controls.
- Reduced-motion media-query and JavaScript branches are covered by static regression checks. The audit browser reported reduced motion disabled; system accessibility settings were not changed.
- Browser console warnings/errors: 0.

## Recovery paths

The browser’s local server was fast enough that the loading panel did not remain visible. Loading, Retry, and Return home presence plus fetch-failure recovery are covered by Python/JavaScript regression tests, including a failed-shard request followed by a successful retry.
