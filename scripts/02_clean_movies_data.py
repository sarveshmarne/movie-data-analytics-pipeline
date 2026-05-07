import pandas as pd
import re
import os
import numpy as np

# Pre-compile regex patterns for performance
_RE_WIKI_REF = re.compile(r"\[.*?\]")
_RE_LEADING_NUM = re.compile(r"^\d+\s*,?\s*")
_RE_PARENS = re.compile(r",?\s*\(.*?\)")
_RE_BRACKETS = re.compile(r"[\[\]]")
_RE_SEPARATORS = re.compile(r"[,;]+")
_RE_WHITESPACE = re.compile(r"\s+")
_RE_CAMEL = re.compile(r"([a-z])([A-Z][a-z]+)")
_RE_CAMEL_SIMPLE = re.compile(r"([a-z])([A-Z])")
_RE_DOUBLE_COMMA = re.compile(r",+")

def clean_text(text):
    """Clean text by removing unwanted characters and formatting"""
    if pd.isna(text):
        return np.nan

    text = str(text).strip()

    # Combined regex cleaning pipeline
    text = _RE_WIKI_REF.sub("", text)
    text = _RE_LEADING_NUM.sub("", text)
    text = _RE_PARENS.sub("", text)
    text = _RE_BRACKETS.sub("", text)
    text = _RE_SEPARATORS.sub(", ", text)
    text = _RE_WHITESPACE.sub(" ", text)

    # Remove trailing commas and spaces
    text = text.strip(" ,")

    return text.strip() if text.strip() else np.nan


def separate_cast_names(cast_text):
    """Separate concatenated cast names with proper spacing"""
    if pd.isna(cast_text):
        return np.nan

    text = str(cast_text).strip()

    # Add comma before capital letters that start new names
    text = _RE_CAMEL.sub(r"\1, \2", text)
    text = _RE_CAMEL_SIMPLE.sub(r"\1, \2", text)
    text = _RE_DOUBLE_COMMA.sub(", ", text)

    return text.strip()


# Load raw data with proper encoding
raw_data_file = "data/raw/movies_2025_complete.csv"
fallback_raw_data_file = "data/raw/movies_2025_fixed.csv"

try:
    df = pd.read_csv(raw_data_file, encoding="utf-8-sig")
except FileNotFoundError:
    try:
        df = pd.read_csv(fallback_raw_data_file, encoding="utf-8-sig")
    except FileNotFoundError:
        print(
            "Error: Raw data file not found. Please run scraper first. "
            f"Expected {raw_data_file}."
        )
        exit(1)

print("Raw data shape:", df.shape)
print("Raw data columns:", list(df.columns))
print("\nRaw data sample:")
print(df.head(10).to_string(index=False))

# Work directly on df — no unnecessary copy needed
df = df.copy()

# Apply text cleaning to basic columns using vectorized .str accessor where possible
basic_columns = ["Name", "Director", "Studio"]
for col in basic_columns:
    if col in df.columns:
        df[col] = df[col].apply(clean_text)

# Apply special cast cleaning to separate concatenated names
if "Cast" in df.columns:
    df["Cast"] = df["Cast"].apply(separate_cast_names).apply(clean_text)

# Data quality filters
print(f"\nBefore filtering: {len(df)} rows")

# Remove rows with empty or invalid names
df = df.dropna(subset=["Name"])
df = df[df["Name"].str.len() > 2]

# Remove exact duplicates based on movie name
df = df.drop_duplicates(subset=["Name"], keep="first")

print(f"After filtering: {len(df)} rows")

# Vectorized cast split — no Python loop overhead
cast_split = df["Cast"].astype(str).str.split(",", n=2, expand=True)
df["Cast_1"] = cast_split[0].replace("nan", np.nan).replace("", np.nan)
df["Cast_2"] = cast_split[1].replace("nan", np.nan).replace("", np.nan)
df["Cast_3"] = cast_split[2].replace("nan", np.nan).replace("", np.nan)

# Add Year and Language columns
df["Year"] = 2025
df["Language"] = "hindi"

# Final column order as specified
final_columns = [
    "Year", "Name", "Director", "Cast_1", "Cast_2", "Cast_3", "Studio", "Language"
]
df = df[final_columns]

# Display cleaned data sample
print("\nCleaned data sample:")
print(df.head(15).to_string(index=False))

# Show some movie examples
print("\nSample movies with director and cast:")
print(df[["Name", "Director", "Cast_1"]].head(10).to_string(index=False))

# Save cleaned data in CSV format with proper encoding
os.makedirs("data/processed", exist_ok=True)
output_file = "data/processed/movies_2025_clean.csv"
df.to_csv(output_file, index=False, encoding="utf-8-sig")

print(f"\n Cleaned data saved to: {output_file}")
print(f"Final dataset: {len(df)} movies")
print(f"Columns: {list(df.columns)}")

