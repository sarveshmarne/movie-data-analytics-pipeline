import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import os

# Pre-compile regex patterns for performance
_BOX_OFFICE_PATTERNS = [
    re.compile(r"Box Office Collection\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
    re.compile(r"Box Office\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
    re.compile(r"Collection\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
    re.compile(r"Net Collection\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
    re.compile(r"Gross\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
    re.compile(r"Worldwide\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
]

_BUDGET_PATTERNS = [
    re.compile(r"Budget\s*[:\-]?\s*([\d.,]+\s*crore)", re.IGNORECASE),
    re.compile(r"Budget\s*[:\-]?\s*([\d.,]+\s*lakh)", re.IGNORECASE),
]

_VERDICT_PATTERNS = [
    re.compile(r"Verdict\s*[:\-]?\s*([A-Za-z\s]+)", re.IGNORECASE),
    re.compile(r"Result\s*[:\-]?\s*([A-Za-z\s]+)", re.IGNORECASE),
    re.compile(r"Status\s*[:\-]?\s*([A-Za-z\s]+)", re.IGNORECASE),
]

_RE_CURRENCY_CLEAN = re.compile(r"[^\d.\s]")
_RE_NUMBER_EXTRACT = re.compile(r"(\d+\.?\d*)")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}


def search_sacnilk(movie_name, year=2025):
    """Search for movie on Sacnilk and return the movie page URL"""
    search_url = f"https://www.sacnilk.com/search?query={movie_name}"

    try:
        response = requests.get(search_url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for search results
        search_results = soup.find_all("a", href=True)

        for result in search_results:
            href = result.get("href", "")
            text = result.get_text().strip()

            # Look for links that contain movie names and match our search
            if "/Movie/" in href and movie_name.lower() in text.lower():
                if str(year) in text or year in text:
                    # Found a matching movie page
                    if href.startswith("/"):
                        return f"https://www.sacnilk.com{href}"
                    else:
                        return href

        return None

    except Exception as e:
        print(f"Search error for {movie_name}: {e}")
        return None


def extract_box_office(movie_url):
    """Extract box office data from Sacnilk movie page"""
    if not movie_url:
        return {}

    try:
        response = requests.get(movie_url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        data = {}
        text_content = soup.get_text()

        # Search for box office patterns using pre-compiled regexes
        for pattern in _BOX_OFFICE_PATTERNS:
            match = pattern.search(text_content)
            if match:
                data["Box_Office"] = match.group(1)
                break

        # Look for budget information
        for pattern in _BUDGET_PATTERNS:
            match = pattern.search(text_content)
            if match:
                data["Budget"] = match.group(1)
                break

        # Look for verdict
        for pattern in _VERDICT_PATTERNS:
            match = pattern.search(text_content)
            if match:
                verdict = match.group(1).strip()
                if any(word in verdict.lower() for word in ["hit", "flop", "blockbuster", "average", "disaster"]):
                    data["Verdict"] = verdict
                    break

        return data

    except Exception as e:
        print(f"Extraction error for {movie_url}: {e}")
        return {}


def convert_currency_to_numeric(value):
    """Convert currency values like '200 crore' or '50 lakh' to absolute numeric values"""
    if not value or pd.isna(value):
        return 0

    value = str(value).strip()
    value = _RE_CURRENCY_CLEAN.sub("", value)
    value = value.strip()

    if not value:
        return 0

    match = _RE_NUMBER_EXTRACT.search(value)
    if not match:
        return 0

    number = float(match.group(1))

    if "crore" in value.lower():
        return int(number * 10_000_000)
    elif "lakh" in value.lower():
        return int(number * 100_000)
    elif "million" in value.lower():
        return int(number * 1_000_000)
    elif "thousand" in value.lower():
        return int(number * 1_000)
    else:
        return int(number)


def enrich_with_sacnilk(df):
    """Enrich dataset with Sacnilk box office data"""
    enriched_rows = []

    for idx, row in df.iterrows():
        movie_name = row["Name"]
        year = row.get("Year", 2025)

        print(f"Processing: {movie_name} ({idx + 1}/{len(df)})")

        # Search on Sacnilk
        movie_url = search_sacnilk(movie_name, year)

        if movie_url:
            box_office_data = extract_box_office(movie_url)

            # Convert currency values to numeric
            if "Box_Office" in box_office_data:
                box_office_data["Box_Office_Numeric"] = convert_currency_to_numeric(
                    box_office_data["Box_Office"]
                )

            if "Budget" in box_office_data:
                box_office_data["Budget_Numeric"] = convert_currency_to_numeric(
                    box_office_data["Budget"]
                )

            # Add source info
            box_office_data["Sacnilk_URL"] = movie_url
            box_office_data["Data_Source"] = "Sacnilk"

        else:
            box_office_data = {
                "Data_Source": "Not Found",
                "Sacnilk_URL": None,
            }

        # Combine with existing data using dict update
        combined = row.to_dict()
        combined.update(box_office_data)
        enriched_rows.append(combined)

        # Rate limiting to avoid being blocked
        time.sleep(2)  # 2 second delay between requests

    return pd.DataFrame(enriched_rows)


def main():
    """Main function to run Sacnilk enrichment"""

    print("Loading final dataset...")
    try:
        df = pd.read_csv("data/final/movies_2025_final.csv", encoding="utf-8-sig")
        print(f"Loaded {len(df)} movies for Sacnilk enrichment")
    except FileNotFoundError:
        print("Error: Final dataset file not found. Please run standardization step first.")
        return

    print("Starting Sacnilk enrichment...")
    print("Note: This process may take several minutes due to rate limiting...")

    # Enrich with Sacnilk data
    enriched_df = enrich_with_sacnilk(df)

    # Save enriched data
    os.makedirs("data/enriched_sacnilk", exist_ok=True)
    enriched_df.to_csv(
        "data/enriched_sacnilk/movies_2025_sacnilk_enriched.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("Sacnilk enrichment complete!")
    print(f"Saved {len(enriched_df)} movies to enriched dataset")

    # Show statistics
    sacnilk_found = enriched_df[enriched_df["Data_Source"] == "Sacnilk"]
    print(
        f"Found box office data for {len(sacnilk_found)} movies "
        f"({len(sacnilk_found) / len(enriched_df) * 100:.1f}%)"
    )

    if len(sacnilk_found) > 0:
        print("\nSample enriched data:")
        sample_cols = ["Name", "Box_Office", "Budget", "Verdict", "Data_Source"]
        available_cols = [col for col in sample_cols if col in enriched_df.columns]
        print(sacnilk_found[available_cols].head(5).to_string(index=False))

    print("\nEnriched dataset saved to: data/enriched_sacnilk/movies_2025_sacnilk_enriched.csv")


if __name__ == "__main__":
    main()

