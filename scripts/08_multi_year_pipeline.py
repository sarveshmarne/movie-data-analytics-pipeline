import pandas as pd
import requests
import os
import re
import time
import random
import numpy as np

# Pre-compile regex patterns
_MONTH_RE = re.compile(r"JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC", flags=re.IGNORECASE)
_RE_CAMEL = re.compile(r"([a-z])([A-Z][a-z]+)")
_RE_CAMEL_SIMPLE = re.compile(r"([a-z])([A-Z])")
_RE_DOUBLE_COMMA = re.compile(r",+")

# Pre-define mock ranges for vectorized generation
_BUDGET_RANGES = np.array([
    [10_000_000, 50_000_000],
    [50_000_000, 150_000_000],
    [150_000_000, 500_000_000],
    [500_000_000, 1_000_000_000],
])


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
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
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

            # Build table via dict — vectorized string stripping
            table_data = {
                "Name": df[title_col].astype(str).str.strip(),
                "Director": df[director_col].astype(str).str.strip(),
                "Cast": df[cast_col].astype(str).str.strip(),
            }
            if studio_col:
                table_data["Studio"] = df[studio_col].astype(str).str.strip()

            table_df = pd.DataFrame(table_data)

            # Remove junk rows using vectorized operations
            table_df = table_df[table_df["Name"].notna()]
            table_df = table_df[~table_df["Name"].str.contains(_MONTH_RE, na=False)]
            table_df = table_df[~table_df["Name"].str.isdigit()]

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
        df_year = df_year.drop_duplicates(subset=["Name"], keep="first")

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

    # Add comma before capital letters that start new names
    text = _RE_CAMEL.sub(r"\1, \2", text)
    text = _RE_CAMEL_SIMPLE.sub(r"\1, \2", text)
    text = _RE_DOUBLE_COMMA.sub(", ", text)

    return text.strip()


def clean_year_data(df, year):
    """Clean data for a specific year using same rules as 2025"""
    print(f"Cleaning data for year {year}...")

    if df.empty:
        print(f"No data to clean for year {year}")
        return df

    # Apply text cleaning to basic columns using vectorized .str.strip()
    basic_columns = ["Name", "Director", "Studio"]
    for col in basic_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Apply special cast cleaning to separate concatenated names
    if "Cast" in df.columns:
        df["Cast"] = df["Cast"].apply(separate_cast_names).astype(str).str.strip()

    # Vectorized cast split — no Python loop overhead
    cast_split = df["Cast"].astype(str).str.split(",", n=2, expand=True)
    df["Cast_1"] = cast_split[0].replace("nan", np.nan).replace("", np.nan)
    df["Cast_2"] = cast_split[1].replace("nan", np.nan).replace("", np.nan)
    df["Cast_3"] = cast_split[2].replace("nan", np.nan).replace("", np.nan)

    # Add Year and Language columns
    df["Year"] = year
    df["Language"] = "hindi"

    # Data quality filters
    print(f"Before filtering: {len(df)} rows")

    # Remove rows with empty or invalid names
    df = df[df["Name"].str.len() > 2]

    # Remove exact duplicates based on movie name
    df = df.drop_duplicates(subset=["Name"], keep="first")

    print(f"After filtering: {len(df)} rows")

    # Select final columns
    final_columns = ["Year", "Name", "Director", "Cast_1", "Cast_2", "Cast_3", "Studio", "Language"]
    available_columns = [col for col in final_columns if col in df.columns]
    df = df[available_columns]

    return df


def enrich_year_data(df, year):
    """Enrich data for a specific year with mock financial data using vectorized numpy"""
    print(f"Enriching data for year {year}...")

    if df.empty:
        print(f"No data to enrich for year {year}")
        return df

    n_rows = len(df)

    # Vectorized mock financial data generation
    range_indices = np.random.randint(0, len(_BUDGET_RANGES), size=n_rows)
    budget_mins = _BUDGET_RANGES[range_indices, 0]
    budget_maxs = _BUDGET_RANGES[range_indices, 1]

    budgets = np.random.randint(budget_mins, budget_maxs)
    success_factors = np.random.uniform(0.8, 4.0, size=n_rows)
    box_offices = (budgets * success_factors).astype(int)

    profits = box_offices - budgets
    roi = np.where(budgets > 0, profits / budgets, 0)

    success_categories = np.where(
        roi > 2, "Blockbuster",
        np.where(roi >= 1, "Hit", "Flop")
    )

    genres_pool = ["Action", "Drama", "Comedy", "Romance", "Thriller"]
    genre_1 = np.random.choice(genres_pool, size=n_rows)
    genre_2 = np.random.choice(genres_pool, size=n_rows)
    imdb = np.round(np.random.uniform(5.0, 8.5, size=n_rows), 1)
    certifications = np.random.choice(["U", "U/A", "A"], size=n_rows)

    # Add columns to df directly — no Python loop
    df["Budget"] = budgets
    df["Box_Office"] = box_offices
    df["Profit"] = profits
    df["ROI"] = roi
    df["Success_Category"] = success_categories
    df["IMDb"] = imdb
    df["Genre_1"] = genre_1
    df["Genre_2"] = genre_2
    df["Verdict"] = success_categories
    df["Certification"] = certifications
    df["data_source"] = f"Mock_{year}"

    return df


def save_raw_data(df, year):
    """Save raw data to Excel format"""
    filename = f"movies_{year}_raw.xlsx"
    filepath = f"data/01_raw/{filename}"

    os.makedirs("data/01_raw", exist_ok=True)
    df.to_excel(filepath, index=False, engine="openpyxl")

    print(f"Raw data saved to: {filepath}")
    return filepath


def save_clean_data(df, year):
    """Save clean data to Excel format"""
    filename = f"movies_{year}_clean.xlsx"
    filepath = f"data/02_processed/{filename}"

    os.makedirs("data/02_processed", exist_ok=True)
    df.to_excel(filepath, index=False, engine="openpyxl")

    print(f"Clean data saved to: {filepath}")
    return filepath


def merge_datasets(df_2024, df_2025):
    """Merge 2024 and 2025 datasets using pd.concat with outer join"""
    print("Merging 2024 and 2025 datasets...")

    # pd.concat with join='outer' automatically aligns columns
    df_merged = pd.concat([df_2024, df_2025], ignore_index=True, join="outer", sort=False)

    # Remove any duplicates (keep first occurrence)
    df_merged = df_merged.drop_duplicates(subset=["Name", "Year"], keep="first")

    print(f"Merged dataset: {len(df_merged)} total movies")
    print(f"2024 movies: {len(df_2024)}")
    print(f"2025 movies: {len(df_2025)}")

    return df_merged


def save_final_dataset(df_merged):
    """Save final merged dataset to Excel"""
    filename = "movies_2024_2025_final.xlsx"
    filepath = f"data/final/{filename}"

    os.makedirs("data/final", exist_ok=True)
    df_merged.to_excel(filepath, index=False, engine="openpyxl")

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
    print("- data/01_raw/movies_2024_raw.xlsx")
    print("- data/02_processed/movies_2024_clean.xlsx")
    print("- data/final/movies_2024_2025_final.xlsx")


if __name__ == "__main__":
    run_multi_year_pipeline()
