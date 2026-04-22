import pandas as pd
import numpy as np
import re
import os

def convert_currency_to_numeric(value):
    """Convert currency values like '200 crore' or '50 lakh' to absolute numeric values"""
    if pd.isna(value) or value == '' or value == 0:
        return 0
    
    value = str(value).strip()
    
    # Remove currency symbols and clean up
    value = re.sub(r'[^\d.\s]', '', value)
    value = value.strip()
    
    if not value or value == '':
        return 0
    
    # Extract number and unit
    number_match = re.search(r'(\d+\.?\d*)', value)
    if not number_match:
        return 0
    
    number = float(number_match.group(1))
    
    # Convert based on unit
    if 'crore' in value.lower():
        return int(number * 10000000)  # 1 crore = 10 million
    elif 'lakh' in value.lower():
        return int(number * 100000)    # 1 lakh = 100 thousand
    elif 'million' in value.lower():
        return int(number * 1000000)   # 1 million
    elif 'thousand' in value.lower():
        return int(number * 1000)      # 1 thousand
    else:
        return int(number)

def standardize_verdict(verdict):
    """Standardize box office verdict to Hit/Flop/Blockbuster/Average"""
    if pd.isna(verdict) or verdict == '' or verdict == 0:
        return 'Average'
    
    verdict = str(verdict).strip().lower()
    
    # Map variations to standard categories
    if any(word in verdict for word in ['blockbuster', 'super hit', 'superhit', 'mega hit']):
        return 'Blockbuster'
    elif any(word in verdict for word in ['hit', 'semi hit', 'average']):
        return 'Hit'
    elif any(word in verdict for word in ['flop', 'disaster', 'below average']):
        return 'Flop'
    else:
        return 'Average'

def split_genres(genres):
    """Split genre string into Genre_1 and Genre_2"""
    if pd.isna(genres) or genres == '' or genres == 0:
        return [np.nan, np.nan]
    
    genres = str(genres).strip()
    
    # Split by common separators
    genre_list = re.split(r'[,;]| and | & ', genres)
    genre_list = [g.strip() for g in genre_list if g.strip()]
    
    # Take first two genres
    result = genre_list[:2] + [np.nan] * (2 - len(genre_list))
    return result

def calculate_success_category(roi):
    """Create success category based on ROI"""
    if pd.isna(roi) or roi == 0:
        return 'Average'
    elif roi > 2:
        return 'Blockbuster'
    elif roi >= 1:
        return 'Hit'
    else:
        return 'Flop'

def standardize_dataset():
    """Main function to standardize and engineer features"""
    
    print("Loading enriched data...")
    try:
        df = pd.read_csv("data/enriched/movies_enriched_2025_hindi.csv", encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies")
    except FileNotFoundError:
        print("Error: Enriched data file not found. Please run enrichment step first.")
        return
    
    print("Standardizing data and engineering features...")
    
    # Create a copy for processing
    df_std = df.copy()
    
    # Step 1: Standardize Budget and Box Office
    print("Converting currency values...")
    if 'Budget' in df_std.columns:
        df_std['Budget'] = df_std['Budget'].apply(convert_currency_to_numeric)
    else:
        df_std['Budget'] = 0
    
    # Add Box_Office column (assuming it might exist, otherwise set to 0)
    if 'Box_Office' in df_std.columns:
        df_std['Box_Office'] = df_std['Box_Office'].apply(convert_currency_to_numeric)
    else:
        df_std['Box_Office'] = 0
    
    # Step 2: Standardize IMDb Rating
    print("Standardizing IMDb ratings...")
    if 'imdb_rating' in df_std.columns:
        df_std['IMDb'] = pd.to_numeric(df_std['imdb_rating'], errors='coerce')
        df_std['IMDb'] = df_std['IMDb'].fillna(0.0)
    else:
        df_std['IMDb'] = 0.0
    
    # Step 3: Split Genres
    print("Processing genres...")
    if 'genres' in df_std.columns:
        genre_split = df_std['genres'].apply(split_genres)
        df_std['Genre_1'] = genre_split.apply(lambda x: x[0])
        df_std['Genre_2'] = genre_split.apply(lambda x: x[1])
    else:
        df_std['Genre_1'] = np.nan
        df_std['Genre_2'] = np.nan
    
    # Step 4: Standardize Verdict
    print("Standardizing verdict...")
    if 'Verdict' in df_std.columns:
        df_std['Verdict'] = df_std['Verdict'].apply(standardize_verdict)
    else:
        df_std['Verdict'] = 'Average'
    
    # Step 5: Create new features
    print("Creating new features...")
    
    # Profit = Box_Office - Budget
    df_std['Profit'] = df_std['Box_Office'] - df_std['Budget']
    
    # ROI = Profit / Budget (handle division by zero)
    df_std['ROI'] = df_std.apply(
        lambda row: row['Profit'] / row['Budget'] if row['Budget'] > 0 else 0,
        axis=1
    )
    
    # Success Category (derived from ROI)
    df_std['Success_Category'] = df_std['ROI'].apply(calculate_success_category)
    
    # Step 6: Final column selection and ordering
    final_columns = [
        'Year', 'Name', 'Director', 'Cast_1', 'Cast_2', 'Cast_3', 'Studio',
        'Budget', 'Box_Office', 'Profit', 'ROI', 'Verdict', 'IMDb',
        'Genre_1', 'Genre_2', 'Language', 'Success_Category'
    ]
    
    # Ensure all required columns exist
    for col in final_columns:
        if col not in df_std.columns:
            df_std[col] = np.nan if col in ['Genre_1', 'Genre_2'] else 0
    
    # Select and reorder columns
    df_final = df_std[final_columns].copy()
    
    # Step 7: Data quality checks
    print("Performing data quality checks...")
    
    # Remove rows with missing critical fields
    df_final = df_final.dropna(subset=['Name', 'Year'])
    
    # Ensure numeric columns are properly typed
    numeric_cols = ['Year', 'Budget', 'Box_Office', 'Profit', 'ROI', 'IMDb']
    for col in numeric_cols:
        df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
    
    print(f"Final dataset: {len(df_final)} movies")
    print(f"Columns: {list(df_final.columns)}")
    
    # Step 8: Save final dataset
    print("Saving final dataset...")
    os.makedirs("data/final", exist_ok=True)
    df_final.to_csv("data/final/movies_2025_final.csv", index=False, encoding="utf-8-sig")
    
    # Display sample data
    print("\nSample of final dataset:")
    print(df_final.head(5).to_string(index=False))
    
    # Display statistics
    print(f"\nDataset Statistics:")
    print(f"Total movies: {len(df_final)}")
    print(f"Average budget: {df_final['Budget'].mean():,.0f}")
    print(f"Average box office: {df_final['Box_Office'].mean():,.0f}")
    print(f"Average profit: {df_final['Profit'].mean():,.0f}")
    print(f"Average ROI: {df_final['ROI'].mean():.2f}")
    print(f"Average IMDb rating: {df_final['IMDb'].mean():.1f}")
    
    print("\nSuccess Category Distribution:")
    print(df_final['Success_Category'].value_counts())
    
    print("\nVerdict Distribution:")
    print(df_final['Verdict'].value_counts())
    
    print("\nGenre Distribution:")
    print(df_final['Genre_1'].value_counts().head(10))
    
    print("Data standardization and feature engineering complete! ")
    print("Final dataset saved to: data/final/movies_2025_final.csv")

if __name__ == "__main__":
    standardize_dataset()
