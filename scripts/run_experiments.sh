#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
WARMUP="${WARMUP:-60}"
DURATION="${DURATION:-360}"
REPEATS="${REPEATS:-10}"
HOST_URL="${HOST_URL:-http://localhost:8080}"
python3 -m pip install -r requirements-loadtest.txt
python3 scripts/run_experiments.py --host "$HOST_URL" --warmup "$WARMUP" --duration "$DURATION" --repeats "$REPEATS"
python3 scripts/analyze_results.py
