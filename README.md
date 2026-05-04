# Global Patent Intelligence Data Pipeline

A data pipeline that pulls real-world patent data from [PatentsView](https://patentsview.org), cleans it, stores it in a database, and generates reports and charts.

## How to run

```bash
pip install -r requirements.txt

python pipeline.py          # loads and cleans the data, builds the database
python reports.py           # generates reports and charts
streamlit run dashboard.py  # launches the interactive dashboard (optional)
```

## Project files

`pipeline.py` reads the raw TSV files, cleans the data, and loads everything into `patents.db`.

`reports.py` queries the database and produces a console report, CSV files, a JSON file, and charts.

`dashboard.py` is an interactive Streamlit dashboard for exploring the data.

`schema.sql` defines the database tables and indexes.

`queries.sql` contains the 7 SQL queries used for analysis.

## Database

The database has 6 tables — patents, inventors, companies, patent_links, classifications, and citations. The patent_links table is what connects everything together, linking each patent to its inventors and the companies that own it.

## Queries

The 7 queries cover the main questions: who are the top inventors, which companies own the most patents, which countries produce the most, how patent counts have changed over the years, and how inventors rank both globally and within their own country.

## Data source

Raw data from [PatentsView](https://patentsview.org/download/data-download-tables). The TSV files go in the `dataset/` folder and are not tracked by git due to their size.
