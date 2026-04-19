import pandas as pd
import os
import requests

def is_valid_movie_row(name):
    """Filter out invalid rows for 2025 data"""
    if not name or not name.strip():
        return False
    
    name = name.strip()
    
    # Skip month headers
    if name.upper() in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']:
        return False
    
    # Skip numeric-only rows
    if name.isdigit():
        return False
    
    # Skip common header/footer text
    invalid_texts = ['title', 'ref.', 'opening', 'rank', 'none', 'director', 'cast', 'studio']
    if name.lower() in invalid_texts:
        return False
    
    # Skip very short names (likely junk)
    if len(name) < 3:
        return False
    
    return True

url = "https://en.wikipedia.org/wiki/List_of_Hindi_films_of_2025"

print("Reading tables from Wikipedia...")
# Download HTML first with headers to avoid 403 error
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
response = requests.get(url, headers=headers)
response.raise_for_status()

# Read tables from the HTML string
tables = pd.read_html(response.text)

all_movies = []

# Process ALL tables that contain movie data
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
    
    print(f"Processing table {i} with columns: {list(df.columns)}")
    
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
    
    # Select relevant columns
    table_df = df[[title_col, director_col, cast_col]].copy()
    if studio_col:
        table_df[studio_col] = df[studio_col]
    
    # Rename columns consistently
    table_df.columns = ["Name", "Director", "Cast"] + (["Studio"] if studio_col else [])
    
    # Remove junk rows
    table_df = table_df[table_df["Name"].notna()]
    table_df = table_df[~table_df["Name"].str.contains("JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC", case=False, na=False)]
    table_df = table_df[~table_df["Name"].astype(str).str.isdigit()]
    
    # Add to collection
    all_movies.append(table_df)

# Combine all tables
if all_movies:
    df = pd.concat(all_movies, ignore_index=True)
    print(f"Combined {len(all_movies)} tables")
else:
    raise Exception("No valid movie tables found")

# Remove duplicates
df = df.drop_duplicates(subset=['Name'], keep='first')

# Save raw data
os.makedirs("data/raw", exist_ok=True)
output_file = "data/raw/movies_2025_all.csv"
df.to_csv(output_file, index=False, encoding="utf-8-sig")

print("2025 Hindi movie scraping completed!")
print(f"Found {len(df)} unique movies")
print("\nSample raw data:")
print(df.head(10).to_string(index=False))