import os

import pandas as pd


INPUT_FILE = "data/03_enriched/movies_enriched_2025_hindi.csv"
OUTPUT_FILE = "data/final/movies_2025_final.csv"


def standardize_dataset():
    """Create the final dataset using only the core movie columns."""
    print("Loading enriched data...")
    try:
        df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies")
    except FileNotFoundError:
        print("Error: Enriched data file not found. Please run enrichment step first.")
        return

    final_columns = [
        "Year",
        "Name",
        "Director",
        "Cast_1",
        "Cast_2",
        "Cast_3",
        "Studio",
        "Language",
    ]

    for col in final_columns:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[final_columns]
    df = df.dropna(subset=["Name"])

    os.makedirs("data/final", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Final dataset: {len(df)} movies")
    print(f"Columns: {list(df.columns)}")
    print(f"Final dataset saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    standardize_dataset()
