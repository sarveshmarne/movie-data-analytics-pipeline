import os

import pandas as pd


INPUT_FILE = "data/02_processed/movies_2025_clean.csv"
OUTPUT_FILE = "data/03_enriched/movies_enriched_2025_hindi.csv"


def add_year_language(df, year=2025, language="hindi"):
    """Add pipeline metadata columns for the enriched dataset."""
    if "Year" not in df.columns:
        df.insert(0, "Year", year)
    else:
        df["Year"] = df["Year"].fillna(year)

    if "Language" not in df.columns:
        df["Language"] = language
    else:
        df["Language"] = df["Language"].fillna(language)

    return df


def main():
    """Create a simple enriched dataset without internet/API columns."""
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    df = add_year_language(df)

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
    df = df[[col for col in final_columns if col in df.columns]]

    os.makedirs("data/03_enriched", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Simple enrichment complete: {OUTPUT_FILE}")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()