# Movie Data Pipeline - Code Efficiency Optimization TODO

## Plan Approved - Implementing Changes

### Step 1: main_pipeline.py
- [x] Replace os.system() with subprocess.run(check=True)
- [x] Add try/except for meaningful error handling

### Step 2: scripts/scrape_wikipedia.py
- [x] Remove dead is_valid_movie_row() function
- [x] Vectorize .apply(lambda x: str(x).strip()) → .astype(str).str.strip()
- [x] Build table_df via dict instead of empty DataFrame
- [x] Pre-compile regex patterns

### Step 3: scripts/clean_movies_data.py
- [x] Combine redundant regex in clean_text() and separate_cast_names()
- [x] Replace cast_split.apply(lambda) with .str.split(expand=True)
- [x] Remove unnecessary df.copy()
- [x] Chain pandas operations

### Step 4: scripts/enrich_movies.py
- [x] Remove unused fuzz and json imports
- [x] Fix input path from .json to .csv
- [x] Minor loop restructuring

### Step 5: scripts/simple_enrich.py
- [x] Vectorize column assignment
- [x] Simplify column reordering

### Step 6: scripts/standardize_data.py
- [x] Vectorize convert_currency_to_numeric()
- [x] Vectorize standardize_verdict()
- [x] Vectorize split_genres()
- [x] Vectorize calculate_success_category()
- [x] Remove unnecessary df.copy()
- [x] Batch pd.to_numeric()

### Step 7: scripts/enhanced_enrichment.py
- [x] Move import random to top level
- [x] Replace hardcoded 132 with len(df)
- [x] Vectorize mock data generation
- [x] Remove unused imports

### Step 8: scripts/multi_year_pipeline.py
- [x] Add missing import numpy as np
- [x] Remove unused imports (BeautifulSoup, datetime, json)
- [x] Move import random to top level
- [x] Vectorize string operations
- [x] Vectorize cast split
- [x] Use pd.concat with join='outer' instead of manual alignment
- [x] General regex optimizations

### Step 9: scripts/sacnilk_scraper.py
- [x] Pre-compile regex patterns at module level
- [x] Optimize enrich_with_sacnilk() loop structure

### Verification
- [x] Check all files for syntax errors
- [x] Confirm no behavioral changes to output

