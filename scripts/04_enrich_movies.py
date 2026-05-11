import os
import time
from difflib import SequenceMatcher

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_URL = "https://api.themoviedb.org/3"
SEARCH_URL = f"{BASE_URL}/search/movie"
MOVIE_URL = f"{BASE_URL}/movie"
OUTPUT_FILE = "data/03_enriched/movies_enriched_2025_hindi.csv"


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


def ensure_genre_columns(df):
    """Make sure the output always has two genre columns."""
    for col in ("Genre_1", "Genre_2"):
        if col not in df.columns:
            df[col] = pd.NA
    return df


def normalize_title(title):
    """Normalize a movie title for matching."""
    return "".join(
        ch.lower() for ch in str(title) if ch.isalnum() or ch.isspace()
    ).strip()


def title_similarity(left, right):
    """Return a fuzzy similarity score between two movie titles."""
    return SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()


def release_year(movie):
    """Extract the release year from a TMDb search result."""
    release_date = movie.get("release_date") or ""
    if len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return None


def score_movie_match(movie, query, expected_year):
    """Score a TMDb result using title similarity and release year."""
    title_score = max(
        title_similarity(query, movie.get("title", "")),
        title_similarity(query, movie.get("original_title", "")),
    )

    year = release_year(movie)
    if year == expected_year:
        year_score = 1.0
    elif year and abs(year - expected_year) == 1:
        year_score = 0.75
    elif year:
        year_score = 0.35
    else:
        year_score = 0.5

    popularity_score = min(float(movie.get("popularity") or 0) / 100, 1)
    return round((title_score * 0.75) + (year_score * 0.20) + (popularity_score * 0.05), 3)


def split_genres(genres):
    """Return the first two TMDb genre names as separate columns."""
    genre_names = [genre.get("name") for genre in genres or [] if genre.get("name")]
    return (
        genre_names[0] if len(genre_names) > 0 else pd.NA,
        genre_names[1] if len(genre_names) > 1 else pd.NA,
    )


def tmdb_auth(api_key):
    """Support either a TMDb v3 API key or a v4 bearer token."""
    if str(api_key).strip().startswith("eyJ"):
        return {"headers": {"Authorization": f"Bearer {api_key}"}, "params": {}}
    return {"headers": {}, "params": {"api_key": api_key}}


def tmdb_get(url, auth, params=None):
    """Call TMDb with the configured auth style."""
    request_params = dict(auth["params"])
    request_params.update(params or {})
    return requests.get(
        url,
        headers=auth["headers"],
        params=request_params,
        timeout=20,
    )


def search_movie(query, year, auth, language="hi-IN"):
    """Search TMDb and return the best title/year match."""
    params = {
        "query": query,
        "primary_release_year": int(year),
        "language": language,
        "include_adult": True,
        "page": 1,
    }

    try:
        response = tmdb_get(SEARCH_URL, auth, params)
        response.raise_for_status()
        candidates = response.json().get("results", [])

        if not candidates:
            return None

        scored = [(score_movie_match(movie, query, int(year)), movie) for movie in candidates]
        score, best_movie = max(scored, key=lambda item: item[0])

        if score < 0.65:
            return None

        return {
            "id": best_movie["id"],
            "score": score,
            "matched_title": best_movie.get("title"),
            "matched_year": release_year(best_movie),
        }
    except Exception as e:
        print(f"Search error for {query}: {e}")
        return None


def get_movie_details(match, auth):
    """Get detailed movie info from TMDb."""
    if not match:
        return {}

    movie_id = match["id"]

    try:
        response = tmdb_get(
            f"{MOVIE_URL}/{movie_id}",
            auth,
            {"language": "en-US"},
        )
        response.raise_for_status()
        movie = response.json()
        genre_1, genre_2 = split_genres(movie.get("genres", []))

        ext_response = tmdb_get(
            f"{MOVIE_URL}/{movie_id}/external_ids",
            auth,
        )
        ext_response.raise_for_status()
        ext_ids = ext_response.json()

        return {
            "tmdb_id": movie_id,
            "imdb_id": ext_ids.get("imdb_id"),
            "imdb_rating": movie.get("vote_average"),
            "genres": ", ".join(
                genre["name"] for genre in movie.get("genres", []) if genre.get("name")
            ),
            "Genre_1": genre_1,
            "Genre_2": genre_2,
            "budget": movie.get("budget", 0),
            "overview": movie.get("overview", ""),
            "release_date": movie.get("release_date", ""),
            "production_companies": [
                company["name"] for company in movie.get("production_companies", [])
            ],
            "matched_title": match.get("matched_title"),
            "matched_year": match.get("matched_year"),
            "match_score": match.get("score"),
        }
    except Exception as e:
        print(f"Details error for {movie_id}: {e}")
        return {}


def enrich_dataframe(df, auth):
    """Enrich the dataframe with TMDb data."""
    enriched_data = []
    total = len(df)

    for idx, row in df.iterrows():
        movie_name = row["Name"]
        movie_year = row["Year"]
        print(f"Processing: {movie_name} ({idx + 1}/{total})")

        tmdb_match = search_movie(movie_name, movie_year, auth)

        if tmdb_match:
            details = get_movie_details(tmdb_match, auth)
            details["wiki_name"] = movie_name
            details["match_method"] = "direct"
        else:
            tmdb_match = search_movie(movie_name, movie_year, auth, "en-US")
            if tmdb_match:
                details = get_movie_details(tmdb_match, auth)
                details["wiki_name"] = movie_name
                details["match_method"] = "en-fallback"
            else:
                details = {
                    "wiki_name": movie_name,
                    "match_method": "no-match",
                    "Genre_1": pd.NA,
                    "Genre_2": pd.NA,
                }

        enriched_data.append(details)
        time.sleep(0.35)

    enriched_df = pd.DataFrame(enriched_data)
    final_df = pd.concat([df.reset_index(drop=True), enriched_df], axis=1)
    return ensure_genre_columns(final_df)


def main():
    """Load cleaned data, enrich it from TMDb, and save the CSV."""
    load_dotenv()

    df = pd.read_csv("data/02_processed/movies_2025_clean.csv", encoding="utf-8-sig")
    df = add_year_language(df)
    print(f"Loaded {len(df)} movies for enrichment")

    api_key = os.getenv("TMDb_API_KEY")
    if not api_key:
        print("No TMDb_API_KEY found. Add it to .env to fetch genres from TMDb.")
        enriched_df = ensure_genre_columns(df)
    else:
        auth = tmdb_auth(api_key)
        enriched_df = enrich_dataframe(df, auth)

    os.makedirs("data/03_enriched", exist_ok=True)
    enriched_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Enrichment complete: {OUTPUT_FILE}")
    print("Genre columns: Genre_1, Genre_2")
    preview_cols = [col for col in ("Name", "Genre_1", "Genre_2", "match_score") if col in enriched_df]
    print(enriched_df[preview_cols].head())


if __name__ == "__main__":
    main()
