import pandas as pd
import numpy as np
import re
import os
import ast

# Pre-compile regex patterns
_RE_CURRENCY_CLEAN = re.compile(r"[^\d.\s]")
_RE_NUMBER_EXTRACT = re.compile(r"(\d+\.?\d*)")


def column_or_default(df, column, default=0):
    """Return a dataframe column or an index-aligned default series."""
    if column in df.columns:
        return df[column]
    return pd.Series(default, index=df.index)


def convert_currency_to_numeric(value):
    """Convert currency values like '200 crore' or '50 lakh' to absolute numeric values"""
    if pd.isna(value) or value == "" or value == 0:
        return 0

    value = str(value).strip().lower()
    value = _RE_CURRENCY_CLEAN.sub("", value)

    if not value:
        return 0

    match = _RE_NUMBER_EXTRACT.search(value)
    if not match:
        return 0

    number = float(match.group(1))

    if "crore" in value:
        return int(number * 10_000_000)
    elif "lakh" in value:
        return int(number * 100_000)
    elif "million" in value:
        return int(number * 1_000_000)
    elif "thousand" in value:
        return int(number * 1_000)
    else:
        return int(number)


def standardize_verdict(verdict):
    """Standardize box office verdict to Hit/Flop/Blockbuster/Average"""
    if pd.isna(verdict) or verdict == "" or verdict == 0:
        return "Average"

    verdict = str(verdict).strip().lower()

    if any(word in verdict for word in ["blockbuster", "super hit", "superhit", "mega hit"]):
        return "Blockbuster"
    elif any(word in verdict for word in ["hit", "semi hit", "average"]):
        return "Hit"
    elif any(word in verdict for word in ["flop", "disaster", "below average"]):
        return "Flop"
    else:
        return "Average"


def split_genre_value(value):
    """Split genre data stored as a comma string or Python-list style string."""
    if pd.isna(value) or value == "":
        return pd.NA, pd.NA

    if isinstance(value, (list, tuple)):
        genres = list(value)
    else:
        text = str(value).strip()
        try:
            parsed = ast.literal_eval(text)
            genres = parsed if isinstance(parsed, (list, tuple)) else [text]
        except (ValueError, SyntaxError):
            genres = re.split(r"[,;]| and | & ", text)

    genres = [str(genre).strip() for genre in genres if str(genre).strip()]
    return (
        genres[0] if len(genres) > 0 else pd.NA,
        genres[1] if len(genres) > 1 else pd.NA,
    )


def standardize_dataset():
    """Main function to standardize and engineer features"""

    print("Loading enriched data...")
    try:
        df = pd.read_csv("data/03_enriched/movies_enriched_2025_hindi.csv", encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies")
    except FileNotFoundError:
        print("Error: Enriched data file not found. Please run enrichment step first.")
        return

    print("Standardizing data and engineering features...")

    # Step 1: Standardize Budget and Box Office
    print("Converting currency values...")
    budget_source = column_or_default(df, "Budget")
    if "budget" in df.columns:
        budget_source = budget_source.mask(budget_source.isna() | (budget_source == 0), df["budget"])
    df["Budget"] = budget_source.apply(convert_currency_to_numeric)
    df["Box_Office"] = column_or_default(df, "Box_Office").apply(convert_currency_to_numeric)

    # Step 2: Standardize IMDb Rating
    print("Standardizing IMDb ratings...")
    df["IMDb"] = pd.to_numeric(column_or_default(df, "imdb_rating"), errors="coerce").fillna(0.0)

    # Step 3: Split Genres (vectorized)
    print("Processing genres...")
    if "Genre_1" not in df.columns:
        df["Genre_1"] = pd.NA
    if "Genre_2" not in df.columns:
        df["Genre_2"] = pd.NA

    if "genres" in df.columns:
        split_genres = df["genres"].apply(split_genre_value)
        df["Genre_1"] = df["Genre_1"].fillna(split_genres.str[0])
        df["Genre_2"] = df["Genre_2"].fillna(split_genres.str[1])

    # Step 4: Standardize Verdict
    print("Standardizing verdict...")
    df["Verdict"] = column_or_default(df, "Verdict", "Average").apply(standardize_verdict)

    # Step 5: Create new features (vectorized)
    print("Creating new features...")

    # Profit = Box_Office - Budget
    df["Profit"] = df["Box_Office"] - df["Budget"]

    # ROI = Profit / Budget (handle division by zero)
    df["ROI"] = np.where(df["Budget"] > 0, df["Profit"] / df["Budget"], 0)

    # Success Category (derived from ROI) — vectorized with pd.cut
    df["Success_Category"] = pd.cut(
        df["ROI"],
        bins=[-np.inf, 0, 1, 2, np.inf],
        labels=["Flop", "Average", "Hit", "Blockbuster"],
        include_lowest=True,
    )
    # pd.cut returns Categorical; convert to string for consistency
    df["Success_Category"] = df["Success_Category"].astype(str)
    # Handle NaN/0 ROI edge cases: anything <= 0 should be Flop/Average
    df.loc[df["ROI"] <= 0, "Success_Category"] = "Flop"
    df.loc[df["ROI"] == 0, "Success_Category"] = "Average"

    # Step 6: Final column selection and ordering
    final_columns = [
        "Year", "Name", "Director", "Cast_1", "Cast_2", "Cast_3", "Studio",
        "Budget", "Box_Office", "Profit", "ROI", "Verdict", "IMDb",
        "Genre_1", "Genre_2", "Language", "Success_Category",
    ]

    # Ensure all required columns exist
    for col in final_columns:
        if col not in df.columns:
            df[col] = np.nan if col in ("Genre_1", "Genre_2") else 0

    # Select and reorder columns
    df = df[final_columns]

    # Step 7: Data quality checks
    print("Performing data quality checks...")

    # Remove rows with missing critical fields
    df = df.dropna(subset=["Name", "Year"])

    # Ensure numeric columns are properly typed — batch operation
    numeric_cols = ["Year", "Budget", "Box_Office", "Profit", "ROI", "IMDb"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    print(f"Final dataset: {len(df)} movies")
    print(f"Columns: {list(df.columns)}")

    # Step 8: Save final dataset
    print("Saving final dataset...")
    os.makedirs("data/final", exist_ok=True)
    df.to_csv("data/final/movies_2025_final.csv", index=False, encoding="utf-8-sig")

    # Display sample data
    print("\nSample of final dataset:")
    print(df.head(5).to_string(index=False))

    # Display statistics
    print(f"\nDataset Statistics:")
    print(f"Total movies: {len(df)}")
    print(f"Average budget: {df['Budget'].mean():,.0f}")
    print(f"Average box office: {df['Box_Office'].mean():,.0f}")
    print(f"Average profit: {df['Profit'].mean():,.0f}")
    print(f"Average ROI: {df['ROI'].mean():.2f}")
    print(f"Average IMDb rating: {df['IMDb'].mean():.1f}")

    print("\nSuccess Category Distribution:")
    print(df["Success_Category"].value_counts())

    print("\nVerdict Distribution:")
    print(df["Verdict"].value_counts())

    print("\nGenre Distribution:")
    print(df["Genre_1"].value_counts().head(10))

    print("Data standardization and feature engineering complete! ")
    print("Final dataset saved to: data/final/movies_2025_final.csv")


if __name__ == "__main__":
    standardize_dataset()
