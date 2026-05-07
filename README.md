# 🎬 Movie Data Analytics Pipeline

End-to-end pipeline for collecting, cleaning, **enriching**, and analyzing Hindi movie data (2025).

## 🚀 Features
✅ Scrapes Wikipedia (BeautifulSoup)  
✅ Cleans & structures data (Pandas)  
✅ **Enriches with TMDb API** (IMDb ratings, genres, budget, studio)  
✅ Full pipeline (`main_pipeline.py`)  
📊 Ready for SQL/Power BI analysis  

## 📁 Data Flow
```
Wikipedia → 01_raw → 02_processed (133 movies) → 03_enriched → SQL → Dashboard
```

## 🛠 Tech Stack
- Python, Pandas, BeautifulSoup, Requests
- TMDb API integration
- Fuzzy matching for name resolution

## 🔑 Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`, add `TMDb_API_KEY`
3. `python main_pipeline.py`

## 📊 Sample Data (processed)
| Year | Name     | Director     | Cast_1       |
|------|----------|--------------|--------------|
| 2025 | Fateh    | Sonu Sood... |              |
| 2025 | Chhaava  | Laxman Utekar| Vicky Kaushal|

**Next:** Database (SQL), Visualization (Power BI), ML predictions

See `TODO.md` for progress.

