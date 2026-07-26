#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m http.server "${PORT:-8000}" --directory docs
