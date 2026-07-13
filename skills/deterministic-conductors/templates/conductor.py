"""General conductor — runs the whole pipeline deterministically.

Same inputs + same config -> same output, every run.
Run:  python conductor.py
"""
import json
import random
from pathlib import Path

try:
    from tqdm import tqdm  # live, in-place progress bar
except ImportError:  # graceful fallback: still runs, just no bar
    def tqdm(it, **_):
        return it

# --- config: seed and paths live here, never hardcoded ---
_cfg = Path("config.json")
CONFIG = json.loads(_cfg.read_text()) if _cfg.exists() else {"seed": 0}


def seed_everything(seed: int) -> None:
    """Seed every source of randomness. Add numpy/torch here if used."""
    random.seed(seed)


def build_pipeline():
    """Return the ordered steps as (label, callable). Import step run()s here."""
    from steps import step1_generate, step2_summarize
    return [
        ("generate", step1_generate.run),
        ("summarize", step2_summarize.run),
    ]


def main() -> None:
    seed_everything(CONFIG.get("seed", 0))
    steps = build_pipeline()
    for label, run in tqdm(steps, desc="pipeline", unit="step"):
        run()


if __name__ == "__main__":
    main()
