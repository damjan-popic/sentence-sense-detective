#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI is not installed or not on PATH." >&2
  exit 1
fi

PROMPT='Read AGENTS.md and CODEX_HANDOVER.md in full. Treat the locked brief as authoritative. Run every required check, audit the current Sentence Sense Detective scaffold in a browser at desktop and mobile widths, and fix only issues that improve correctness, accessibility, clarity, or deployment readiness. Do not add new product features, do not alter reviewed answers without documenting the issue and adding a regression test, and do not expose any private development metadata in docs/.'

if [[ "${1:-}" == "--exec" ]]; then
  codex exec "$PROMPT"
else
  printf '%s\n\n' "Start Codex in this repository and paste the following prompt:" "$PROMPT"
  codex
fi
