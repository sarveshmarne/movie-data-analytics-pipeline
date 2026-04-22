import pandas as pd
import requests
import os
import time
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()

API_KEY = os.getenv('TMDb_API_KEY')
if not API_KEY:
    print("⚠️ No TMDb_API_KEY found. Creating basic enrichment only.")
    API_KEY = None

BASE_URL = "https://api.themoviedb.org/3"
SEARCH_URL = f"{BASE_URL}/search/movie"
MOVIE_URL = f"{BASE_URL}/movie"

headers = {
    "Authorization": f"Bearer {API_KEY}"
} if API_KEY else {}

def search_movie_enhanced(query, year=2025, language='hi-IN'):
    """Enhanced search for movie on TMDb with multiple strategies"""
    if not API_KEY:
        return None
    
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
            # Try to find exact match first
            for result in data['results']:
                if query.lower() in result['title'].lower():
                    return result['id']
            
            # If no exact match, return first result
            return data['results'][0]['id']
        return None
    except Exception as e:
        print(f"Search error for {query}: {e}")
        return None

def get_movie_details_enhanced(movie_id):
    """Get detailed info including budget and revenue"""
    if not movie_id or not API_KEY:
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
            "revenue": movie.get('revenue', 0),  # This is box office
            "overview": movie.get('overview', ''),
            "release_date": movie.get('release_date', ''),
            "production_companies": [c['name'] for c in movie.get('production_companies', [])],
            "popularity": movie.get('popularity', 0),
            "vote_count": movie.get('vote_count', 0),
            "data_source": "TMDb"
        }
        return details
    except Exception as e:
        print(f"Details error for {movie_id}: {e}")
        return {}

def create_mock_financial_data():
    """Create realistic mock financial data for demonstration"""
    import random
    
    # Realistic ranges for Hindi movies
    budget_ranges = [
        (10000000, 50000000),    # 1-5 crore
        (50000000, 150000000),   # 5-15 crore  
        (150000000, 500000000),  # 15-50 crore
        (500000000, 1000000000)  # 50-100 crore
    ]
    
    data = []
    for i in range(132):  # Number of movies
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
        
        data.append({
            'Budget': budget,
            'Box_Office': box_office,
            'Profit': profit,
            'ROI': roi,
            'Success_Category': success_category,
            'data_source': 'Mock_Demo'
        })
    
    return data

def enhance_dataset():
    """Main enrichment function with fallback strategies"""
    
    print("Loading final dataset...")
    try:
        df = pd.read_csv("data/final/movies_2025_final.csv", encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies for enhancement")
    except FileNotFoundError:
        print("Error: Final dataset file not found. Please run standardization step first.")
        return
    
    print("Starting enhanced enrichment...")
    
    if API_KEY:
        print("Using TMDb API for real data...")
        enriched_data = []
        
        for idx, row in df.iterrows():
            movie_name = row['Name']
            year = row.get('Year', 2025)
            
            print(f"Processing: {movie_name} ({idx+1}/{len(df)})")
            
            # Search TMDb
            tmdb_id = search_movie_enhanced(movie_name, year)
            
            if tmdb_id:
                details = get_movie_details_enhanced(tmdb_id)
                details['wiki_name'] = movie_name
                details['match_method'] = 'direct'
            else:
                details = {
                    'wiki_name': movie_name,
                    'match_method': 'no-match',
                    'data_source': 'No_Data'
                }
            
            enriched_data.append(details)
            time.sleep(0.5)  # Rate limit
        
        enriched_df = pd.DataFrame(enriched_data)
        
        # Combine with original data
        final_df = pd.concat([df.reset_index(drop=True), enriched_df], axis=1)
        
    else:
        print("Using mock financial data for demonstration...")
        mock_data = create_mock_financial_data()
        
        # Add mock data to original dataframe
        df['Budget'] = [d['Budget'] for d in mock_data]
        df['Box_Office'] = [d['Box_Office'] for d in mock_data]
        df['Profit'] = [d['Profit'] for d in mock_data]
        df['ROI'] = [d['ROI'] for d in mock_data]
        df['Success_Category'] = [d['Success_Category'] for d in mock_data]
        df['data_source'] = 'Mock_Demo'
        
        final_df = df.copy()
    
    # Ensure all required columns exist
    required_columns = [
        'Year', 'Name', 'Director', 'Cast_1', 'Cast_2', 'Cast_3', 'Studio',
        'Budget', 'Box_Office', 'Profit', 'ROI', 'Verdict', 'IMDb',
        'Genre_1', 'Genre_2', 'Language', 'Success_Category'
    ]
    
    for col in required_columns:
        if col not in final_df.columns:
            if col in ['Budget', 'Box_Office', 'Profit', 'ROI', 'IMDb']:
                final_df[col] = 0
            elif col in ['Genre_1', 'Genre_2']:
                final_df[col] = None
            else:
                final_df[col] = 'Unknown'
    
    # Select and reorder columns
    final_df = final_df[required_columns].copy()
    
    # Save enhanced dataset
    os.makedirs("data/enhanced", exist_ok=True)
    final_df.to_csv("data/enhanced/movies_2025_enhanced.csv", index=False, encoding="utf-8-sig")
    
    print("Enhanced enrichment complete!")
    print(f"Saved {len(final_df)} movies to enhanced dataset")
    
    # Display statistics
    if 'Budget' in final_df.columns:
        print(f"\nDataset Statistics:")
        print(f"Total movies: {len(final_df)}")
        print(f"Average budget: {final_df['Budget'].mean():,.0f}")
        print(f"Average box office: {final_df['Box_Office'].mean():,.0f}")
        print(f"Average profit: {final_df['Profit'].mean():,.0f}")
        print(f"Average ROI: {final_df['ROI'].mean():.2f}")
        
        if 'IMDb' in final_df.columns:
            print(f"Average IMDb rating: {final_df['IMDb'].mean():.1f}")
        
        print("\nSuccess Category Distribution:")
        print(final_df['Success_Category'].value_counts())
        
        print("\nData Source Distribution:")
        if 'data_source' in final_df.columns:
            print(final_df['data_source'].value_counts())
        else:
            print("No data_source column found")
    
    # Show sample
    print("\nSample enhanced data:")
    sample_cols = ['Name', 'Budget', 'Box_Office', 'Profit', 'ROI', 'Success_Category', 'IMDb']
    available_cols = [col for col in sample_cols if col in final_df.columns]
    print(final_df[available_cols].head(5).to_string(index=False))
    
    print("\nEnhanced dataset saved to: data/enhanced/movies_2025_enhanced.csv")

if __name__ == "__main__":
    enhance_dataset()
