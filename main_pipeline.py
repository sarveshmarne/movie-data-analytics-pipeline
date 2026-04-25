#!/usr/bin/env python3
"""
Main Movie Data Pipeline - End-to-End Execution
Runs: scrape → clean → enrich
"""

import os
import sys
import subprocess
from pathlib import Path


def run_step(step_name, script_path):
    """Run a pipeline step with proper error handling."""
    print(f"🚀 Running {step_name}...")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(f"✅ {step_name} complete!")
    except subprocess.CalledProcessError as e:
        print(f"❌ {step_name} failed with exit code {e.returncode}")
        print(e.stdout)
        print(e.stderr)
        raise


if __name__ == "__main__":
    print("🎬 Movie Data Pipeline Starting...")

    # Check API key (optional now)
    api_key = os.getenv('TMDb_API_KEY')
    if not api_key:
        print("⚠️ No TMDb_API_KEY - skipping enrichment step (add to .env for full features)")
        ENRICH = False
    else:
        ENRICH = True
        print("✅ TMDb API ready")

    # 1. Scrape
    run_step("Scrape Wikipedia", "scripts/scrape_wikipedia.py")

    # 2. Clean
    run_step("Clean Data", "scripts/clean_movies_data.py")

    # 3. Enrich (optional)
    if ENRICH:
        run_step("Enrich with TMDb", "scripts/enrich_movies.py")
    else:
        print("⏭️ Skipping enrichment (no API key)")

    print("🎉 Pipeline Complete!")
    print("📁 Check data/enriched/movies_enriched_2025_hindi.csv")

