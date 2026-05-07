import pandas as pd
import re

debug_df = pd.read_csv('data/debug_all_movies.csv')
missing_movies = ['Badass Ravi Kumar', 'Sunny Sanskari Ki Tulsi Kumari']
month_re = re.compile(r'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC', flags=re.IGNORECASE)

for movie in missing_movies:
    row = debug_df[debug_df.Name == movie]
    name_str = str(row.Name.iloc[0])
    print(f'Movie: {movie}')
    print(f'Name as stored: "{name_str}"')
    print(f'Name length: {len(name_str)}')
    print(f'Is digit: {name_str.isdigit()}')
    print(f'Contains month: {bool(month_re.search(name_str))}')
    print()
