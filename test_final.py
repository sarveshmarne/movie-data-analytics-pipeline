import pandas as pd

current_df = pd.read_csv('data/01_raw/movies_2025_complete.csv')
missing_movies = ['Sunny Sanskari Ki Tulsi Kumari', 'Badass Ravi Kumar']

for movie in missing_movies:
    found = movie in current_df.Name.values
    print(f'{movie}: {" FOUND" if found else " NOT FOUND"}')

print(f'\nTotal movies: {len(current_df)}')
print(f'All movies: {sorted(current_df.Name.tolist())}')
