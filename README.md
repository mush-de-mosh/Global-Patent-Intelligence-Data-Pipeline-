# Global Patent Intelligence Data Pipeline

A data engineering project that collects, cleans, stores, and analyzes
real-world patent data from [PatentsView](https://patentsview.org).

---

## Project Structure

```
cloud_assignment/
├── pipeline.py          # Stage 1-4: ingest → clean → export CSVs → load DB
├── reports.py           # Stage 5:   console + CSV + JSON reports + charts
├── dashboard.py         # Bonus:     Streamlit interactive dashboard
├── queries.sql          # All 7 SQL analysis queries (standalone)
├── schema.sql           # Database schema: CREATE TABLE + indexes
├── requirements.txt
├── README.md
├── data/                # Clean CSV exports (git-tracked)
│   ├── clean_patents.csv
│   ├── clean_inventors.csv
│   └── clean_companies.csv
├── reports/             # Generated reports: CSV, JSON, PNG charts
└── dataset/             # Raw TSV files — gitignored (too large)
```

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place raw TSV files in dataset/

# 3. Run the pipeline (ingest, clean, load DB, export clean CSVs)
python pipeline.py

# 4. Generate all reports (console, CSV, JSON, charts)
python reports.py

# 5. Launch interactive dashboard (optional)
streamlit run dashboard.py
```

---

## Pipeline Stages

| Stage | Script | What it does |
|-------|--------|-------------|
| 1 | `pipeline.py` | Reads raw TSV files in 100,000-row chunks |
| 2 | `pipeline.py` | Cleans data with pandas (nulls, dates, whitespace) |
| 3 | `pipeline.py` | Exports `clean_patents.csv`, `clean_inventors.csv`, `clean_companies.csv` |
| 4 | `pipeline.py` | Loads SQLite database using `schema.sql` |
| 5 | `reports.py`  | Console report, CSV exports, JSON report, PNG charts |

---

## Database Tables

| Table | Description |
|-------|-------------|
| `patents` | patent_id, title, abstract, filing_date, year |
| `inventors` | inventor_id, name, city, state, country |
| `companies` | company_id, name, type, city, state, country |
| `patent_links` | Relationship table: patent ↔ inventor ↔ company |
| `classifications` | USPC classification codes per patent |
| `citations` | Patent citation relationships |

---

## SQL Queries

| Query | Question |
|-------|----------|
| Q1 | Who are the top inventors by patent count? |
| Q2 | Which companies own the most patents? |
| Q3 | Which countries produce the most patents? |
| Q4 | How many patents are granted each year? (+ YoY change) |
| Q5 | JOIN across patents, inventors, and companies |
| Q6 | CTE — leading company per country |
| Q7 | Window functions — global and per-country inventor rankings |

---

## Reports Generated

| File | Type |
|------|------|
| Console output | Terminal printed report |
| `reports/top_inventors.csv` | Top inventors by patent count |
| `reports/top_companies.csv` | Top companies by patent count |
| `reports/country_trends.csv` | Patents and inventors per country |
| `reports/yearly_trends.csv` | Patents granted per year |
| `reports/top_categories.csv` | Top USPC patent categories |
| `reports/inventor_ranking.csv` | Inventor rankings with window functions |
| `reports/patent_report.json` | Full JSON report |
| `reports/chart_top_inventors.png` | Bar chart |
| `reports/chart_top_companies.png` | Bar chart |
| `reports/chart_yearly_trends.png` | Line chart |
| `reports/chart_top_countries.png` | Bar chart |
| `reports/chart_categories_pie.png` | Pie chart |

---

## Data Sources

Raw files from [PatentsView Bulk Data Downloads](https://patentsview.org/download/data-download-tables):

| File | Contents |
|------|----------|
| `g_patent.tsv` | Patent titles, abstracts, grant dates |
| `g_application.tsv` | Filing dates |
| `g_inventor_disambiguated.tsv` | Disambiguated inventor records |
| `g_assignee_disambiguated.tsv` | Disambiguated company records |
| `g_assignee_not_disambiguated.tsv` | Raw assignee data |
| `g_persistent_assignee.tsv` | Patent-to-assignee links |
| `g_location_disambiguated.tsv` | City, state, country per location |
| `g_uspc_at_issue.tsv` | USPC classification codes |
| `g_us_patent_citation.tsv` | Citation relationships |
