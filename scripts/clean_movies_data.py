import pandas as pd
import re
import os
import numpy as np

def clean_text(text):
    """Clean text by removing unwanted characters and formatting"""
    if pd.isna(text):
        return np.nan
    
    text = str(text).strip()
    
    # Remove Wikipedia references and citations
    text = re.sub(r"\[.*?\]", "", text)
    
    # Remove leading numbers and commas
    text = re.sub(r"^\d+\s*,?\s*", "", text)
    
    # Remove special markers like (alpha)
    text = re.sub(r",?\s*\(.*?\)", "", text)
    
    # Remove remaining brackets
    text = re.sub(r"[\[\]]", "", text)
    
    # Normalize separators
    text = re.sub(r"[,;]+", ", ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    
    # Remove trailing commas and spaces
    text = text.strip(" ,")
    
    return text.strip() if text.strip() else np.nan

def split_cast(cast):
    """Split cast into Cast_1, Cast_2, Cast_3 columns"""
    if pd.isna(cast):
        return [np.nan, np.nan, np.nan]
    
    cast_list = [c.strip() for c in str(cast).split(',') if c.strip()]
    result = cast_list[:3] + [np.nan] * (3 - len(cast_list))
    return result

# Load raw data with proper encoding
try:
    df = pd.read_csv("data/raw/movies_2025_all.csv", encoding="utf-8-sig")
except FileNotFoundError:
    print("Error: Raw data file not found. Please run scraper first.")
    exit(1)

print("Raw data shape:", df.shape)
print("Raw data columns:", list(df.columns))
print("\nRaw data sample:")
print(df.head(10).to_string(index=False))

# Create a copy for cleaning
df_clean = df.copy()

# Apply text cleaning to basic columns
basic_columns = ['Name', 'Director', 'Cast', 'Studio']
for col in basic_columns:
    if col in df_clean.columns:
        df_clean[col] = df_clean[col].apply(clean_text)

# Data quality filters
print(f"\nBefore filtering: {len(df_clean)} rows")

# Remove rows with empty or invalid names
df_clean = df_clean.dropna(subset=['Name'])
df_clean = df_clean[df_clean['Name'].str.len() > 2]

# Remove exact duplicates based on movie name
df_clean = df_clean.drop_duplicates(subset=['Name'], keep='first')

print(f"After filtering: {len(df_clean)} rows")

# Split cast into Cast_1, Cast_2, Cast_3
cast_split = df_clean['Cast'].apply(split_cast)
df_clean['Cast_1'] = cast_split.apply(lambda x: x[0])
df_clean['Cast_2'] = cast_split.apply(lambda x: x[1])
df_clean['Cast_3'] = cast_split.apply(lambda x: x[2])

# Add Year and Language columns
df_clean['Year'] = 2025
df_clean['Language'] = 'hindi'

# Final column order as specified
final_columns = ['Year', 'Name', 'Director', 'Cast_1', 'Cast_2', 'Cast_3', 'Studio', 'Language']
df_clean = df_clean[final_columns]

# Display cleaned data sample
print("\nCleaned data sample:")
print(df_clean.head(15).to_string(index=False))

# Show some movie examples
print("\nSample movies with director and cast:")
print(df_clean[['Name', 'Director', 'Cast_1']].head(10).to_string(index=False))

# Save cleaned data in CSV format with proper encoding
os.makedirs("data/processed", exist_ok=True)
output_file = "data/processed/movies_2025_clean.csv"
df_clean.to_csv(output_file, index=False, encoding="utf-8-sig")

print(f"\n Cleaned data saved to: {output_file}")
print(f"Final dataset: {len(df_clean)} movies")
print(f"Columns: {list(df_clean.columns)}")
