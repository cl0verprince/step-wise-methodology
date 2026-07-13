#!/usr/bin/env bash
# General conductor — runs the whole pipeline deterministically.
# Same inputs + same config -> same output, every run.
# Run:  ./conductor.sh
set -euo pipefail

# --- config: seed and paths live here, never hardcoded ---
SEED="${SEED:-0}"
export SEED                 # each step reads $SEED and seeds itself

# Ordered pipeline: one function per step — no eval, arguments stay intact.
step_generate()  { python steps/step1_generate.py; }
step_summarize() { python steps/step2_summarize.py; }

steps=(step_generate step_summarize)

total=${#steps[@]}
start=$(date +%s)
hashes="####################"   # 20 chars: bar fill / padding by slicing
dots="...................."

for i in "${!steps[@]}"; do
  "${steps[$i]}"

  # In-place progress bar: percentage + filled/empty bar + elapsed
  done_n=$((i + 1))
  pct=$((done_n * 100 / total))
  filled=$((done_n * 20 / total))
  printf "\r  [%s%s] %d%%  %ds" \
    "${hashes:0:filled}" "${dots:0:20-filled}" "$pct" "$(( $(date +%s) - start ))"
done
printf "\n"
