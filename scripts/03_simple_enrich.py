import pandas as pd
import os


def simple_enrich():
    """Simple enrichment to add Year and Language columns"""

    # Load cleaned CSV data
    try:
        df = pd.read_csv("data/02_processed/movies_2025_clean.csv", encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies from cleaned CSV")
    except FileNotFoundError:
        print("Error: Cleaned data file not found. Please run cleaning step first.")
        return

    # Add Year and Language columns (vectorized, no conditionals needed)
    df["Year"] = 2025
    df["Language"] = "hindi"
    print("Added Year column with value 2025")
    print("Added Language column with value 'hindi'")

    # Reorder columns to put Year and Language first
    cols = ["Year", "Language"] + [col for col in df.columns if col not in ("Year", "Language")]
    df = df[cols]

    # Save enriched data
    os.makedirs("data/03_enriched", exist_ok=True)
    output_file = "data/03_enriched/movies_enriched_2025_hindi.csv"
    try:
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
    except PermissionError:
        print(
            f"\nError: Cannot save {output_file} because the file is open or locked.\n"
            "Close it in Excel, Power BI, VS Code preview, or any other app, then run this script again."
        )
        return

    print("Simple enrichment complete!")
    print(f"Saved {len(df)} movies to enriched CSV")
    print(f"Columns: {list(df.columns)}")

    # Show sample
    print("\nSample enriched data:")
    print(df.head(3).to_string(index=False))


if __name__ == "__main__":
    simple_enrich()
