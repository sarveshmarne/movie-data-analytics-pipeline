#!/usr/bin/env python3
"""
Main Movie Data Pipeline - End-to-End Execution
Runs: scrape -> clean -> enrich
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "scripts"


def print_process_output(output):
    """Print subprocess output without crashing on Windows console encodings."""
    if not output:
        return
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.buffer.write(output.encode(encoding, errors="replace"))
    if not output.endswith("\n"):
        sys.stdout.buffer.write(b"\n")
    sys.stdout.flush()


def run_step(step_name, script_path):
    """Run a pipeline step with proper error handling."""
    print(f"Running {step_name}...", flush=True)

    script_file = Path(script_path)
    if not script_file.is_absolute():
        script_file = ROOT_DIR / script_file

    if not script_file.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_file}")

    child_env = os.environ.copy()
    child_env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(script_file)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=ROOT_DIR,
            env=child_env,
        )
        print_process_output(result.stdout)
        print(f"{step_name} complete!", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"{step_name} failed with exit code {e.returncode}", flush=True)
        print_process_output(e.stdout)
        print_process_output(e.stderr)
        raise


if __name__ == "__main__":
    print("Movie Data Pipeline Starting...", flush=True)

    load_dotenv(ROOT_DIR / ".env")

    # Check API key (optional now)
    api_key = os.getenv("TMDb_API_KEY")
    if not api_key:
        print("No TMDb_API_KEY - enrichment will copy cleaned data only", flush=True)
    else:
        print("TMDb API ready", flush=True)

    # 1. Scrape
    run_step("Scrape Wikipedia", SCRIPTS_DIR / "01_scrape_wikipedia.py")

    # 2. Clean
    run_step("Clean Data", SCRIPTS_DIR / "02_clean_movies_data.py")

    # 3. Enrich. Without an API key, this copies cleaned data to the enriched folder.
    run_step("Enrich with TMDb", SCRIPTS_DIR / "03_enrich_movies.py")

    print("Pipeline Complete!", flush=True)
    print("Check data/03_enriched/movies_enriched_2025_hindi.csv", flush=True)
