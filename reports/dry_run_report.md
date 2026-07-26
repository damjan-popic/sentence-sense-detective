# Sentence Sense Detective 10K dry-run report

**Status:** complete locally; not pushed or deployed.

## Sources and retrieval

Both official ANC hosts presented an expired TLS certificate during this run. The fetcher required an explicit opt-in, restricted the exception to the two ANC hostnames, and verified the recorded archive hashes.

### MASC 3.0.0

- Official page: https://anc.org/data/masc/downloads/data-download/
- Archive: `masc_500k_texts.zip` (1,351,682 bytes)
- SHA-256: `0c3f1fd3314ee5ec09830d6f6b217c19a6899d1cabd22c42264578c3348b2d01`
- Licence/terms: CC BY 3.0 US
- Selected sentences: 7,781
- TLS certificate verified: `false`

### OANC GrAF release 2011-07-16

- Official page: https://anc.org/data/oanc/download/
- Archive: `OANC_GrAF.zip` (655,230,430 bytes)
- SHA-256: `5a26559a1becba41a527cb674fff4fb9c4fb70b276f60422c4f07a0ef23fd867`
- Licence/terms: Unrestricted use and redistribution for research and development, including commercial development (official OANC download terms)
- Selected sentences: 2,219
- TLS certificate verified: `false`

## Corpus audit and selection

- MASC audit: 390 documents, 36,469 raw sentences, 594,220 tokens.
- OANC fallback audit: 60 of 653 deterministically extracted written documents, 15,874 raw sentences, 408,174 tokens.
- Accepted: 10,000 unique IDs and 10,000 unique normalized texts.
- Sources: MASC: 7,781, OANC: 2,219.
- Difficulty: advanced: 2,000, basic: 3,500, intermediate: 4,500.
- Genres: blog: 952, court: 150, debate: 150, email: 761, essay: 550, ficlets: 375, fiction: 416, government: 700, journal: 557, letters: 1,144, movie-script: 330, newspaper: 791, nonfiction: 640, spoken: 340, technical: 1,110, travel: 1,034.
- OANC fallback used: `true` (2,219 sentences).
- Maximum document contribution: 75 sentences.
- Selection seed/filter: `20260726` / `1.5.0`.
- Selection SHA-256: `004ba9c33cf1929490cac1881e9867a3eb466357471c3718a60b3aa3f75fe806`.
- Rejections by reason: fragment_or_missing_terminal_punctuation: 9,601, no_finite_verb: 7,371, excluded_genre: 7,228, too_few_lexical_tokens: 7,186, too_many_digits_or_symbols: 3,264, too_many_lexical_tokens: 2,397, encoding_or_unmatched_delimiter: 1,526, no_high_confidence_question: 1,218, all_caps: 586, header_or_list_fragment: 555, markup_or_formula: 316, email_address: 302, exact_duplicate: 191, url: 83, unsuitable_content: 79, phone_number: 57, near_duplicate: 55, excessive_punctuation: 52, public_technical_terminology: 48, source_extraction_artifact: 39, private_data: 26, file_path: 1.

## Annotation and question generation

- Stanza 1.14.0 / Torch 2.13.0+cu130; processors: `tokenize,mwt,pos,lemma,depparse`.
- GPU: `true` (NVIDIA RTX 2000 Ada Generation); model bundle `51f32c3b4b77d2a460e8aeaeb653dbd240ad270b7f8b42110f509ff87c483711`.
- Annotated sentences: 10,000; final resumable run: 42.035 seconds.
- Candidates: 35,358; auto-accepted: 34,858; needs review: 500; rejected: 0.
- Accepted by mode: clauses: 5,492, parts-of-speech: 19,999, sentence-elements: 9,367.
- Questions per sentence: 1 = 0, 2 = 522, 3+ = 9,478.
- Question generation was run twice and was byte-identical.

## Public site and review deliverables

- Public questions: 35,014 across 10,092 displayed sentences, including the preserved pilot.
- Immutable reviewed core: 106.
- Manifest: 32,204 bytes.
- Shards: 89; size range 23,772–273,207 bytes.
- Initial transfer: 100,519 / 500,000 bytes.
- Total static site: 21,840,699 bytes.
- Full review workbook: 35,358 rows, 6,365,226 bytes.
- Deterministic sample workbook: 100 rows, 24,644 bytes.
- Release archive: 3,948,813 bytes; SHA-256 `2bd3269bc9f9ce3f6db4df5ef95c1359477e4e8b8e53f8c4703c579535d93f4c`.

## Verification

- `make validate`: passed.
- Python: 31 tests passed; JavaScript: 13 tests passed.
- Workbook inspect/error scans and rendered previews: passed.
- Browser: desktop and mobile practice/About/quiz/summary checked; no console errors.
- Responsive widths: 320, 390, 768, and 1440 px; no horizontal overflow.
- Initial browser load requested the manifest but no gold/shard data until a mode started.
- About dialog scrolls at narrow widths and retains the exact approved copy.
- Screenshot evidence: `reports/screenshots/`.

## Stop condition

Python dependencies were installed only in the ignored project `.venv`; Stanza models use the local user cache. No push, release upload, GitHub Pages action, or deployment was performed. The branch remains local for review.
