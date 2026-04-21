import pandas as pd
import requests
import os
import time
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
import json

# Load environment variables
load_dotenv()

API_KEY = os.getenv('TMDb_API_KEY')
if not API_KEY:
    print("⚠️ No TMDb_API_KEY found. Skipping enrichment (add to .env for full features).")
    os.makedirs("data/enriched", exist_ok=True)
    df_base = pd.read_json("data/processed/movies_cleaned_2025_hindi.json")
    df_base.to_json("data/enriched/movies_enriched_2025_hindi.json", orient='records', indent=2)
    print("✅ Demo enrichment complete - base data copied to enriched JSON!")
    exit()

BASE_URL = "https://api.themoviedb.org/3"
SEARCH_URL = f"{BASE_URL}/search/movie"
MOVIE_URL = f"{BASE_URL}/movie"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

def search_movie(query, year=2025, language='hi-IN'):
    """Search for movie on TMDb with fuzzy matching."""
    params = {
        "query": query,
        "year": year,
        "language": language,
        "include_adult": True,
        "page": 1
    }
    
    try:
        response = requests.get(SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            return data['results'][0]['id']  # Return best match ID
        return None
    except Exception as e:
        print(f"Search error for {query}: {e}")
        return None

def get_movie_details(movie_id):
    """Get detailed info for movie."""
    if not movie_id:
        return {}
    
    try:
        # Movie details
        response = requests.get(f"{MOVIE_URL}/{movie_id}", headers=headers, params={"language": "en-US"})
        response.raise_for_status()
        movie = response.json()
        
        # External IDs (IMDb)
        ext_response = requests.get(f"{MOVIE_URL}/{movie_id}/external_ids", headers=headers)
        ext_response.raise_for_status()
        ext_ids = ext_response.json()
        
        details = {
            "tmdb_id": movie_id,
            "imdb_id": ext_ids.get('imdb_id'),
            "imdb_rating": movie.get('vote_average'),
            "genres": [g['name'] for g in movie.get('genres', [])],
            "budget": movie.get('budget', 0),
            "overview": movie.get('overview', ''),
            "release_date": movie.get('release_date', ''),
            "production_companies": [c['name'] for c in movie.get('production_companies', [])],
            "match_score": 100  # Default for direct match
        }
        return details
    except Exception as e:
        print(f"Details error for {movie_id}: {e}")
        return {}

def enrich_dataframe(df):
    """Enrich the dataframe with TMDb data."""
    enriched_data = []
    
    for idx, row in df.iterrows():
        movie_name = row['Name']
        print(f"Processing: {movie_name} ({idx+1}/{len(df)})")
        
        # Search TMDb
        tmdb_id = search_movie(movie_name, row['Year'])
        
        if tmdb_id:
            details = get_movie_details(tmdb_id)
            details['wiki_name'] = movie_name
            details['match_method'] = 'direct'
        else:
            # Fallback: try English search
            tmdb_id = search_movie(movie_name, row['Year'], 'en-US')
            if tmdb_id:
                details = get_movie_details(tmdb_id)
                details['wiki_name'] = movie_name
                details['match_method'] = 'en-fallback'
            else:
                details = {'wiki_name': movie_name, 'match_method': 'no-match'}
        
        enriched_data.append(details)
        
        time.sleep(0.5)  # Rate limit
        
    enriched_df = pd.DataFrame(enriched_data)
    final_df = pd.concat([df.reset_index(drop=True), enriched_df], axis=1)
    return final_df

if __name__ == "__main__":
    # Load cleaned data
    df = pd.read_json("data/processed/movies_cleaned_2025_hindi.json")
    print(f"Loaded {len(df)} movies for enrichment")
    
    # Add Year and Language columns if they don't exist
    if 'Year' not in df.columns:
        df['Year'] = 2025
    if 'Language' not in df.columns:
        df['Language'] = 'hindi'
    
    # Enrich
    enriched_df = enrich_dataframe(df)
    
    # Save as JSON
    os.makedirs("data/enriched", exist_ok=True)
    enriched_df.to_json("data/enriched/movies_enriched_2025_hindi.json", orient='records', indent=2)
    
    print("✅ Enrichment complete as JSON!")
    print("New columns: tmdb_id, imdb_id, imdb_rating, genres, budget...")
    print(enriched_df[['Name', 'imdb_rating', 'genres', 'budget']].head())

