import pandas as pd
import requests
import os
import time
from dotenv import load_dotenv


def add_year_language(df, year=2025, language="hindi"):
    """Add pipeline metadata columns for the enriched dataset."""
    if "Year" not in df.columns:
        df.insert(0, "Year", year)
    else:
        df["Year"] = df["Year"].fillna(year)

    if "Language" not in df.columns:
        df["Language"] = language
    else:
        df["Language"] = df["Language"].fillna(language)

    return df


# Load environment variables
load_dotenv()

API_KEY = os.getenv("TMDb_API_KEY")
if not API_KEY:
    print("⚠️ No TMDb_API_KEY found. Skipping enrichment (add to .env for full features).")
    os.makedirs("data/03_enriched", exist_ok=True)
    df_base = pd.read_csv("data/02_processed/movies_2025_clean.csv", encoding="utf-8-sig")
    df_base = add_year_language(df_base)
    df_base.to_csv("data/03_enriched/movies_enriched_2025_hindi.csv", index=False, encoding="utf-8-sig")
    print("✅ Demo enrichment complete - base data copied to enriched CSV!")
    exit()

BASE_URL = "https://api.themoviedb.org/3"
SEARCH_URL = f"{BASE_URL}/search/movie"
MOVIE_URL = f"{BASE_URL}/movie"

headers = {"Authorization": f"Bearer {API_KEY}"}


def search_movie(query, year=2025, language="hi-IN"):
    """Search for movie on TMDb with fuzzy matching."""
    params = {
        "query": query,
        "year": year,
        "language": language,
        "include_adult": True,
        "page": 1,
    }

    try:
        response = requests.get(SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data["results"]:
            return data["results"][0]["id"]  # Return best match ID
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
        response = requests.get(
            f"{MOVIE_URL}/{movie_id}",
            headers=headers,
            params={"language": "en-US"},
        )
        response.raise_for_status()
        movie = response.json()

        # External IDs (IMDb)
        ext_response = requests.get(
            f"{MOVIE_URL}/{movie_id}/external_ids", headers=headers
        )
        ext_response.raise_for_status()
        ext_ids = ext_response.json()

        return {
            "tmdb_id": movie_id,
            "imdb_id": ext_ids.get("imdb_id"),
            "imdb_rating": movie.get("vote_average"),
            "genres": [g["name"] for g in movie.get("genres", [])],
            "budget": movie.get("budget", 0),
            "overview": movie.get("overview", ""),
            "release_date": movie.get("release_date", ""),
            "production_companies": [
                c["name"] for c in movie.get("production_companies", [])
            ],
            "match_score": 100,  # Default for direct match
        }
    except Exception as e:
        print(f"Details error for {movie_id}: {e}")
        return {}


def enrich_dataframe(df):
    """Enrich the dataframe with TMDb data."""
    enriched_data = []
    total = len(df)

    for idx, row in df.iterrows():
        movie_name = row["Name"]
        print(f"Processing: {movie_name} ({idx + 1}/{total})")

        # Search TMDb
        tmdb_id = search_movie(movie_name, row["Year"])

        if tmdb_id:
            details = get_movie_details(tmdb_id)
            details["wiki_name"] = movie_name
            details["match_method"] = "direct"
        else:
            # Fallback: try English search
            tmdb_id = search_movie(movie_name, row["Year"], "en-US")
            if tmdb_id:
                details = get_movie_details(tmdb_id)
                details["wiki_name"] = movie_name
                details["match_method"] = "en-fallback"
            else:
                details = {"wiki_name": movie_name, "match_method": "no-match"}

        enriched_data.append(details)
        time.sleep(0.5)  # Rate limit

    enriched_df = pd.DataFrame(enriched_data)
    final_df = pd.concat([df.reset_index(drop=True), enriched_df], axis=1)
    return final_df


if __name__ == "__main__":
    # Load cleaned data
    df = pd.read_csv("data/02_processed/movies_2025_clean.csv", encoding="utf-8-sig")
    df = add_year_language(df)
    print(f"Loaded {len(df)} movies for enrichment")

    # Enrich
    enriched_df = enrich_dataframe(df)

    # Save as CSV
    os.makedirs("data/03_enriched", exist_ok=True)
    enriched_df.to_csv(
        "data/03_enriched/movies_enriched_2025_hindi.csv", index=False, encoding="utf-8-sig"
    )

    print("✅ Enrichment complete as CSV!")
    print("New columns: tmdb_id, imdb_id, imdb_rating, genres, budget...")
    print(enriched_df[["Name", "imdb_rating", "genres", "budget"]].head())

