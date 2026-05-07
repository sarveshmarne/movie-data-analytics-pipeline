import pandas as pd
import requests
from bs4 import BeautifulSoup
import os

def debug_scrape():
    """Debug scraper to find missing movies"""
    
    url = "https://en.wikipedia.org/wiki/List_of_Hindi_films_of_2025"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print("Debug: Fetching Wikipedia page...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Read all tables
    tables = pd.read_html(response.text)
    print(f"Debug: Found {len(tables)} total tables")
    
    all_movies = []
    
    # Process ALL tables
    for i, df in enumerate(tables):
        print(f"\nDebug: Table {i}")
        print(f"Debug: Columns: {list(df.columns)}")
        print(f"Debug: Shape: {df.shape}")
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        cols_lower = [str(c).lower() for c in df.columns]
        
        # Check if this table has movie data
        has_title = any("title" in col for col in cols_lower)
        has_director = any("director" in col for col in cols_lower)
        has_cast = any("cast" in col for col in cols_lower)
        
        print(f"Debug: Has title: {has_title}, director: {has_director}, cast: {has_cast}")
        
        if has_title and has_director and has_cast:
            # Find column names
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
            
            print(f"Debug: Found columns - Title: {title_col}, Director: {director_col}, Cast: {cast_col}, Studio: {studio_col}")
            
            if title_col and director_col and cast_col:
                # Extract data
                table_movies = []
                for _, row in df.iterrows():
                    name = str(row[title_col]).strip()
                    director = str(row[director_col]).strip()
                    cast = str(row[cast_col]).strip()
                    studio = str(row[studio_col]).strip() if studio_col else ''
                    
                    # Skip invalid rows
                    if (not name or name == 'nan' or len(name) < 3 or
                        name.upper() in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] or
                        name.isdigit() or
                        name.lower() in ['title', 'ref.', 'opening', 'rank', 'none', 'director', 'cast', 'studio']):
                        continue
                    
                    table_movies.append({
                        'Name': name,
                        'Director': director,
                        'Cast': cast,
                        'Studio': studio,
                        'Table': i
                    })
                
                print(f"Debug: Extracted {len(table_movies)} movies from table {i}")
                print(f"Debug: Sample movies: {[m['Name'] for m in table_movies[:5]]}")
                
                all_movies.extend(table_movies)
    
    print(f"\nDebug: Total movies extracted: {len(all_movies)}")
    
    # Check for duplicates
    names = [m['Name'] for m in all_movies]
    unique_names = list(set(names))
    print(f"Debug: Unique movie names: {len(unique_names)}")
    
    # Show all movie names
    print(f"\nDebug: All movie names:")
    for i, movie in enumerate(all_movies):
        print(f"{i+1:3d}. {movie['Name']} (Table {movie['Table']})")
    
    # Save debug data
    df_debug = pd.DataFrame(all_movies)
    df_debug.to_csv("data/debug_all_movies.csv", index=False, encoding="utf-8-sig")
    print(f"\nDebug: Saved all extracted movies to data/debug_all_movies.csv")

if __name__ == "__main__":
    debug_scrape()
