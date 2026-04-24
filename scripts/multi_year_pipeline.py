import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
import time
from datetime import datetime
import json

def generate_wikipedia_url(base_year=2025, target_year=2024):
    """Generate Wikipedia URL for target year based on base year pattern"""
    base_url = "https://en.wikipedia.org/wiki/List_of_Hindi_films_of_2025"
    return base_url.replace(str(base_year), str(target_year))

def scrape_year_data(year):
    """Scrape movie data for a specific year"""
    print(f"Scraping data for year {year}...")
    
    # Generate URL for the target year
    url = generate_wikipedia_url(2025, year)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        print(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Read tables from HTML
        tables = pd.read_html(response.text)
        
        all_movies = []
        
        # Process ALL tables that contain movie data (same logic as 2025)
        for i, df in enumerate(tables):
            # Clean column names
            df.columns = [str(c).strip() for c in df.columns]
            cols_lower = [str(c).lower() for c in df.columns]
            
            # Check if this table has movie data (flexible detection)
            has_title = any("title" in col for col in cols_lower)
            has_director = any("director" in col for col in cols_lower)
            has_cast = any("cast" in col for col in cols_lower)
            
            # Skip tables without basic movie structure
            if not (has_title and has_director and has_cast):
                continue
            
            print(f"Processing table {i} for year {year} with columns: {list(df.columns)}")
            
            # Find actual column names (case-insensitive)
            title_col = None
            director_col = None
            cast_col = None
            studio_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if "title" in col_lower and title_col is None:
                    title_col = col
                elif "director" in col_lower and director_col is None:
                    director_col = col
                elif "cast" in col_lower and cast_col is None:
                    cast_col = col
                elif "studio" in col_lower and studio_col is None:
                    studio_col = col
            
            # Skip if essential columns missing
            if title_col is None or director_col is None or cast_col is None:
                continue
            
            # Select relevant columns with proper separator extraction
            table_df = pd.DataFrame()
            table_df["Name"] = df[title_col].apply(lambda x: str(x).strip())
            table_df["Director"] = df[director_col].apply(lambda x: str(x).strip())
            table_df["Cast"] = df[cast_col].apply(lambda x: str(x).strip())
            if studio_col:
                table_df["Studio"] = df[studio_col].apply(lambda x: str(x).strip())
            
            # Remove junk rows
            table_df = table_df[table_df["Name"].notna()]
            table_df = table_df[~table_df["Name"].str.contains("JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC", case=False, na=False)]
            table_df = table_df[~table_df["Name"].astype(str).str.isdigit()]
            
            # Add year column
            table_df["Year"] = year
            
            # Add to collection
            all_movies.append(table_df)
        
        # Combine all tables
        if all_movies:
            df_year = pd.concat(all_movies, ignore_index=True)
            print(f"Combined {len(all_movies)} tables for year {year}")
        else:
            raise Exception(f"No valid movie tables found for year {year}")
        
        # Remove duplicates
        df_year = df_year.drop_duplicates(subset=['Name'], keep='first')
        
        print(f"Found {len(df_year)} unique movies for year {year}")
        return df_year
        
    except Exception as e:
        print(f"Error scraping year {year}: {e}")
        return pd.DataFrame()

def separate_cast_names(cast_text):
    """Separate concatenated cast names with proper spacing"""
    if pd.isna(cast_text):
        return np.nan
    
    text = str(cast_text).strip()
    
    # Add comma before capital letters that start new names (except first letter)
    # This handles cases like "Actor1 Actor2 Actor3" -> "Actor1, Actor2, Actor3"
    text = re.sub(r'([a-z])([A-Z][a-z]+)', r'\1, \2', text)
    
    # Handle cases where there might be no space between names
    text = re.sub(r'([a-z])([A-Z])', r'\1, \2', text)
    
    # Clean up any double commas
    text = re.sub(r',+', ', ', text)
    
    return text.strip()

def clean_year_data(df, year):
    """Clean data for a specific year using same rules as 2025"""
    print(f"Cleaning data for year {year}...")
    
    if df.empty:
        print(f"No data to clean for year {year}")
        return df
    
    df_clean = df.copy()
    
    # Apply text cleaning to basic columns
    basic_columns = ['Name', 'Director', 'Studio']
    for col in basic_columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(lambda x: str(x).strip() if pd.notna(x) else '')
    
    # Apply special cast cleaning to separate concatenated names
    if 'Cast' in df_clean.columns:
        df_clean['Cast'] = df_clean['Cast'].apply(separate_cast_names)
        df_clean['Cast'] = df_clean['Cast'].apply(lambda x: str(x).strip() if pd.notna(x) else '')
    
    # Split cast into Cast_1, Cast_2, Cast_3
    def split_cast(cast):
        """Split cast into Cast_1, Cast_2, Cast_3 columns"""
        if pd.isna(cast) or cast == '':
            return ['', '', '']
        
        cast_list = [c.strip() for c in str(cast).split(',') if c.strip()]
        result = cast_list[:3] + [''] * (3 - len(cast_list))
        return result
    
    cast_split = df_clean['Cast'].apply(split_cast)
    df_clean['Cast_1'] = cast_split.apply(lambda x: x[0])
    df_clean['Cast_2'] = cast_split.apply(lambda x: x[1])
    df_clean['Cast_3'] = cast_split.apply(lambda x: x[2])
    
    # Add Year and Language columns
    df_clean['Year'] = year
    df_clean['Language'] = 'hindi'
    
    # Data quality filters
    print(f"Before filtering: {len(df_clean)} rows")
    
    # Remove rows with empty or invalid names
    df_clean = df_clean[df_clean['Name'].str.len() > 2]
    
    # Remove exact duplicates based on movie name
    df_clean = df_clean.drop_duplicates(subset=['Name'], keep='first')
    
    print(f"After filtering: {len(df_clean)} rows")
    
    # Select final columns
    final_columns = ['Year', 'Name', 'Director', 'Cast_1', 'Cast_2', 'Cast_3', 'Studio', 'Language']
    available_columns = [col for col in final_columns if col in df_clean.columns]
    df_clean = df_clean[available_columns].copy()
    
    return df_clean

def enrich_year_data(df, year):
    """Enrich data for a specific year with mock financial data"""
    print(f"Enriching data for year {year}...")
    
    if df.empty:
        print(f"No data to enrich for year {year}")
        return df
    
    # Create realistic mock financial data
    import random
    
    # Realistic ranges for Hindi movies (adjust by year if needed)
    budget_ranges = [
        (10000000, 50000000),    # 1-5 crore
        (50000000, 150000000),   # 5-15 crore  
        (150000000, 500000000),  # 15-50 crore
        (500000000, 1000000000)  # 50-100 crore
    ]
    
    enriched_data = []
    for _, row in df.iterrows():
        budget_min, budget_max = random.choice(budget_ranges)
        budget = random.randint(budget_min, budget_max)
        
        # Box office typically 1.5-3x budget for successful movies
        success_factor = random.uniform(0.8, 4.0)
        box_office = int(budget * success_factor)
        
        # Calculate derived metrics
        profit = box_office - budget
        roi = profit / budget if budget > 0 else 0
        
        # Determine success category
        if roi > 2:
            success_category = 'Blockbuster'
        elif roi >= 1:
            success_category = 'Hit'
        else:
            success_category = 'Flop'
        
        # Create enriched row
        enriched_row = row.to_dict()
        enriched_row.update({
            'Budget': budget,
            'Box_Office': box_office,
            'Profit': profit,
            'ROI': roi,
            'Success_Category': success_category,
            'IMDb': round(random.uniform(5.0, 8.5), 1),
            'Genre_1': random.choice(['Action', 'Drama', 'Comedy', 'Romance', 'Thriller']),
            'Genre_2': random.choice(['Drama', 'Action', 'Romance', 'Comedy', 'Thriller']),
            'Verdict': success_category,
            'Certification': random.choice(['U', 'U/A', 'A']),
            'data_source': f'Mock_{year}'
        })
        
        enriched_data.append(enriched_row)
    
    return pd.DataFrame(enriched_data)

def save_raw_data(df, year):
    """Save raw data to Excel format"""
    filename = f"movies_{year}_raw.xlsx"
    filepath = f"data/raw/{filename}"
    
    os.makedirs("data/raw", exist_ok=True)
    df.to_excel(filepath, index=False, engine='openpyxl')
    
    print(f"Raw data saved to: {filepath}")
    return filepath

def save_clean_data(df, year):
    """Save clean data to Excel format"""
    filename = f"movies_{year}_clean.xlsx"
    filepath = f"data/processed/{filename}"
    
    os.makedirs("data/processed", exist_ok=True)
    df.to_excel(filepath, index=False, engine='openpyxl')
    
    print(f"Clean data saved to: {filepath}")
    return filepath

def merge_datasets(df_2024, df_2025):
    """Merge 2024 and 2025 datasets"""
    print("Merging 2024 and 2025 datasets...")
    
    # Ensure both datasets have same columns
    all_columns = set(df_2024.columns) | set(df_2025.columns)
    
    # Add missing columns with empty values
    for col in all_columns:
        if col not in df_2024.columns:
            df_2024[col] = ''
        if col not in df_2025.columns:
            df_2025[col] = ''
    
    # Reorder columns consistently
    common_columns = sorted(all_columns)
    df_2024 = df_2024[common_columns]
    df_2025 = df_2025[common_columns]
    
    # Concatenate datasets
    df_merged = pd.concat([df_2024, df_2025], ignore_index=True)
    
    # Remove any duplicates (keep first occurrence)
    df_merged = df_merged.drop_duplicates(subset=['Name', 'Year'], keep='first')
    
    print(f"Merged dataset: {len(df_merged)} total movies")
    print(f"2024 movies: {len(df_2024)}")
    print(f"2025 movies: {len(df_2025)}")
    
    return df_merged

def save_final_dataset(df_merged):
    """Save final merged dataset to Excel"""
    filename = "movies_2024_2025_final.xlsx"
    filepath = f"data/final/{filename}"
    
    os.makedirs("data/final", exist_ok=True)
    df_merged.to_excel(filepath, index=False, engine='openpyxl')
    
    print(f"Final merged dataset saved to: {filepath}")
    return filepath

def scrape_year(target_year):
    """Main function to scrape a specific year"""
    print(f"=== Starting Multi-Year Pipeline for {target_year} ===")
    
    # Step 1: Scrape raw data
    df_raw = scrape_year_data(target_year)
    
    if df_raw.empty:
        print(f"Failed to scrape data for year {target_year}")
        return None
    
    # Step 2: Save raw data
    save_raw_data(df_raw, target_year)
    
    # Step 3: Clean data
    df_clean = clean_year_data(df_raw, target_year)
    
    # Step 4: Save clean data
    save_clean_data(df_clean, target_year)
    
    # Step 5: Enrich data
    df_enriched = enrich_year_data(df_clean, target_year)
    
    return df_enriched

def run_multi_year_pipeline():
    """Main function to run complete multi-year pipeline"""
    print("=== Multi-Year Movie Data Pipeline ===")
    print("This pipeline will collect, clean, and merge movie data across years")
    
    # Load existing 2025 dataset (reference)
    try:
        df_2025 = pd.read_csv("data/enhanced/movies_2025_enhanced.csv", encoding="utf-8-sig")
        print(f"Loaded 2025 reference dataset: {len(df_2025)} movies")
    except FileNotFoundError:
        print("Warning: 2025 enhanced dataset not found. Will scrape 2025 as well.")
        df_2025 = scrape_year(2025)
    
    # Step 1-5: Process 2024 data
    df_2024 = scrape_year(2024)
    
    if df_2024 is None or df_2024.empty:
        print("Failed to process 2024 data. Pipeline stopped.")
        return
    
    # Step 6: Merge datasets
    df_merged = merge_datasets(df_2024, df_2025)
    
    # Step 7: Save final merged dataset
    save_final_dataset(df_merged)
    
    print("\n=== Pipeline Complete ===")
    print("Multi-year dataset successfully created!")
    print("Files created:")
    print("- data/raw/movies_2024_raw.xlsx")
    print("- data/processed/movies_2024_clean.xlsx") 
    print("- data/final/movies_2024_2025_final.xlsx")

if __name__ == "__main__":
    run_multi_year_pipeline()
