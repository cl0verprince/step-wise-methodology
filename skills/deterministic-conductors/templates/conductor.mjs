// General conductor — runs the whole pipeline deterministically.
// Same inputs + same config -> same output, every run.
// Run:  node conductor.mjs
import { readFileSync, existsSync } from "node:fs";

// --- config: seed and paths live here, never hardcoded ---
const CONFIG = existsSync("config.json")
  ? JSON.parse(readFileSync("config.json", "utf8"))
  : { seed: 0 };

// Node's Math.random() is not seedable, so use a seeded PRNG (mulberry32)
// and pass `rng` into every step that needs randomness.
function makeRng(seed) {
  let a = seed >>> 0;
  return function rng() {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// In-place progress bar: percentage + filled/empty bar + elapsed.
function progress(done, total, start) {
  const pct = Math.round((done / total) * 100);
  const filled = Math.round((done / total) * 20);
  const bar = "█".repeat(filled) + "░".repeat(20 - filled);
  const secs = ((Date.now() - start) / 1000).toFixed(1);
  process.stdout.write(`\r  ${bar} ${pct}%  ${secs}s`);
  if (done === total) process.stdout.write("\n");
}

async function main() {
  const rng = makeRng(CONFIG.seed);
  const { run: generate } = await import("./steps/step1_generate.mjs");
  const { run: summarize } = await import("./steps/step2_summarize.mjs");
  const steps = [["generate", generate], ["summarize", summarize]];

  const start = Date.now();
  for (let i = 0; i < steps.length; i++) {
    await steps[i][1](rng);
    progress(i + 1, steps.length, start);
  }
}

main();
