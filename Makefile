PYTHON := .venv/bin/python

.PHONY: corpus-fetch corpus-fetch-oanc corpus-extract corpus-models corpus-audit \
	corpus-audit-oanc corpus-select corpus-annotate corpus-generate \
	corpus-review-pack corpus-build-public corpus-package corpus-all \
	remap-contract remap-compile remap-replay-gold remap-10k \
	remap-review-pack remap-compare remap-all validate preview

corpus-fetch:
	$(PYTHON) scripts/fetch_corpus.py --source masc --allow-insecure-tls

corpus-fetch-oanc:
	$(PYTHON) scripts/fetch_corpus.py --source oanc --allow-insecure-tls

corpus-extract:
	$(PYTHON) scripts/extract_masc.py
	$(PYTHON) scripts/extract_oanc.py

corpus-models:
	$(PYTHON) scripts/annotate_stanza.py --download-models

corpus-audit:
	$(PYTHON) scripts/extract_masc.py
	$(PYTHON) scripts/audit_corpus.py

corpus-audit-oanc:
	$(PYTHON) scripts/extract_oanc.py
	$(PYTHON) scripts/audit_corpus.py --corpus OANC --input external/oanc \
		--output external/audit/oanc_sentence_candidates.jsonl \
		--report reports/oanc_audit.json --markdown reports/oanc_audit.md \
		--max-documents 60

corpus-select:
	$(PYTHON) scripts/select_sentences.py

corpus-annotate:
	$(PYTHON) scripts/annotate_stanza.py

corpus-generate: remap-10k

remap-contract:
	$(PYTHON) scripts/validate_formal_contract.py

remap-compile: remap-contract
	$(PYTHON) scripts/extract_tagset.py
	$(PYTHON) scripts/build_gold_index.py
	$(PYTHON) scripts/compile_remap_rules.py

remap-replay-gold: remap-compile
	$(PYTHON) scripts/replay_gold_contract.py

remap-10k: remap-replay-gold
	$(PYTHON) scripts/remap_stanza_annotations.py
	$(PYTHON) scripts/generate_questions.py
	$(PYTHON) scripts/report_remap_distribution.py

remap-review-pack:
	$(PYTHON) scripts/prepare_review_rows.py
	powershell.exe -NoProfile -ExecutionPolicy Bypass \
		-File "$$(wslpath -m scripts/export_review_pack.ps1)" \
		-RepoRoot "$$(wslpath -m .)"

remap-compare:
	$(PYTHON) scripts/compare_legacy_and_formal_banks.py

remap-all:
	$(MAKE) remap-10k
	$(MAKE) remap-review-pack
	$(MAKE) remap-compare
	$(MAKE) corpus-build-public
	$(MAKE) corpus-package
	$(MAKE) validate

corpus-review-pack:
	$(PYTHON) scripts/prepare_review_rows.py
	powershell.exe -NoProfile -ExecutionPolicy Bypass \
		-File "$$(wslpath -m scripts/export_review_pack.ps1)" \
		-RepoRoot "$$(wslpath -m .)"

corpus-build-public:
	$(PYTHON) scripts/build_public_shards.py

corpus-package:
	$(PYTHON) scripts/package_corpus_release.py

corpus-all: corpus-fetch corpus-models corpus-audit corpus-fetch-oanc \
	corpus-audit-oanc corpus-select corpus-annotate corpus-generate \
	corpus-review-pack corpus-build-public corpus-package validate

validate:
	$(PYTHON) scripts/build_public_shards.py --check
	$(PYTHON) scripts/validate_corpus.py
	$(PYTHON) scripts/validate_public_shards.py
	$(PYTHON) scripts/validate_data.py
	$(PYTHON) -m unittest discover -s tests -v
	node --check docs/assets/round-state.js
	node --check docs/assets/question-bank.js
	node --check docs/assets/app.js
	node --test tests/test_round_state.js tests/test_question_bank.js

preview:
	$(PYTHON) -m http.server 8000 --directory docs
