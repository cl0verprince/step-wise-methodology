#!/usr/bin/env bash
# General conductor — runs the whole pipeline deterministically.
# Same inputs + same config -> same output, every run.
# Run:  ./conductor.sh
set -euo pipefail

# --- config: seed and paths live here, never hardcoded ---
SEED="${SEED:-0}"
export SEED                 # each step reads $SEED and seeds itself

# Ordered pipeline: "label:command"
steps=(
  "generate:python steps/step1_generate.py"
  "summarize:python steps/step2_summarize.py"
)

total=${#steps[@]}
start=$(date +%s)

for i in "${!steps[@]}"; do
  label="${steps[$i]%%:*}"
  cmd="${steps[$i]#*:}"
  eval "$cmd"

  # In-place progress bar: percentage + filled/empty bar + elapsed
  done=$((i + 1))
  pct=$((done * 100 / total))
  filled=$((done * 20 / total))
  bar=$(printf '%0.s#' $(seq 1 "$filled"))
  pad=$(printf '%0.s.' $(seq 1 $((20 - filled))))
  printf "\r  [%s%s] %d%%  %ds" "$bar" "$pad" "$pct" "$(( $(date +%s) - start ))"
done
printf "\n"
