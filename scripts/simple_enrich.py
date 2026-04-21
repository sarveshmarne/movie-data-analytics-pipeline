import pandas as pd
import os

def simple_enrich():
    """Simple enrichment to add Year and Language columns"""
    
    # Load cleaned CSV data
    try:
        df = pd.read_csv("data/processed/movies_2025_clean.csv", encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies from cleaned CSV")
    except FileNotFoundError:
        print("Error: Cleaned data file not found. Please run cleaning step first.")
        return
    
    # Add Year and Language columns if they don't exist
    if 'Year' not in df.columns:
        df['Year'] = 2025
        print("Added Year column with value 2025")
    
    if 'Language' not in df.columns:
        df['Language'] = 'hindi'
        print("Added Language column with value 'hindi'")
    
    # Reorder columns to put Year and Language first
    if 'Year' in df.columns and 'Language' in df.columns:
        cols = ['Year', 'Language'] + [col for col in df.columns if col not in ['Year', 'Language']]
        df = df[cols]
    
    # Save enriched data
    os.makedirs("data/enriched", exist_ok=True)
    df.to_csv("data/enriched/movies_enriched_2025_hindi.csv", index=False, encoding="utf-8-sig")
    
    print("Simple enrichment complete!")
    print(f"Saved {len(df)} movies to enriched CSV")
    print(f"Columns: {list(df.columns)}")
    
    # Show sample
    print("\nSample enriched data:")
    print(df.head(3).to_string(index=False))

if __name__ == "__main__":
    simple_enrich()
