"""
Global Patent Intelligence -- Reports
=======================================
Generates:
  A. Console report  (terminal)
  B. CSV exports     -->  reports/
  C. JSON report     -->  reports/patent_report.json
  D. PNG charts      -->  reports/  [extra marks]

Run:
    python reports.py
"""

import os
import json
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "patents.db") 
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

con = sqlite3.connect(DB_PATH)
# redirect SQLite temp files to D: (C: has almost no free space)
con.execute("PRAGMA temp_store=FILE")
con.execute("PRAGMA temp_store_directory='D:\\\\tmp_pipeline'")
con.execute("PRAGMA cache_size=-65536")   # 64 MB page cache


def q(sql):
    return pd.read_sql(sql, con)


# ── run all queries ───────────────────────────────────────────────────────────
total_patents   = q("SELECT COUNT(*) AS n FROM patents").iloc[0]["n"]
total_inventors = q("SELECT COUNT(*) AS n FROM inventors").iloc[0]["n"]
total_companies = q("SELECT COUNT(*) AS n FROM companies").iloc[0]["n"]

top_inventors = q("""
    SELECT i.name                        AS inventor,
           i.country,
           COUNT(DISTINCT pl.patent_id)  AS patents
    FROM   patent_links pl
    JOIN   inventors i ON pl.inventor_id = i.inventor_id
    WHERE  i.name != ''
    GROUP  BY i.inventor_id
    ORDER  BY patents DESC
    LIMIT  10
""")

top_companies = q("""
    SELECT c.name                        AS company,
           c.country,
           COUNT(DISTINCT pl.patent_id)  AS patents
    FROM   patent_links pl
    JOIN   companies c ON pl.company_id = c.company_id
    WHERE  c.name IS NOT NULL
    GROUP  BY c.company_id
    ORDER  BY patents DESC
    LIMIT  10
""")

top_countries = q("""
    SELECT i.country,
           COUNT(DISTINCT pl.patent_id)   AS total_patents,
           COUNT(DISTINCT pl.inventor_id) AS total_inventors,
           ROUND(
               100.0 * COUNT(DISTINCT pl.patent_id) /
               (SELECT COUNT(DISTINCT patent_id) FROM patent_links), 4
           ) AS share_pct
    FROM   patent_links pl
    JOIN   inventors i ON pl.inventor_id = i.inventor_id
    WHERE  i.country IS NOT NULL
    GROUP  BY i.country
    ORDER  BY total_patents DESC
    LIMIT  15
""")

yearly_trends = q("""
    SELECT year,
           COUNT(*) AS total_patents
    FROM   patents
    WHERE  year IS NOT NULL
      AND  year BETWEEN 1990 AND 2024
    GROUP  BY year
    ORDER  BY year
""")

top_categories = q("""
    SELECT mainclass_id,
           COUNT(DISTINCT patent_id) AS patents
    FROM   classifications
    WHERE  mainclass_id IS NOT NULL
    GROUP  BY mainclass_id
    ORDER  BY patents DESC
    LIMIT  10
""")

inventor_ranking = q("""
    WITH counts AS (
        SELECT i.inventor_id,
               i.name    AS inventor,
               i.country,
               COUNT(DISTINCT pl.patent_id) AS patents
        FROM   patent_links pl
        JOIN   inventors i ON pl.inventor_id = i.inventor_id
        WHERE  i.name != '' AND i.country IS NOT NULL
        GROUP  BY i.inventor_id
    )
    SELECT inventor, country, patents,
           RANK() OVER (ORDER BY patents DESC)                      AS global_rank,
           RANK() OVER (PARTITION BY country ORDER BY patents DESC) AS rank_in_country
    FROM   counts
    ORDER  BY global_rank
    LIMIT  20
""")


# ══════════════════════════════════════════════════════════════════════════════
# A. CONSOLE REPORT
# ══════════════════════════════════════════════════════════════════════════════
W = 56

def div(c="="):  print(c * W)
def sec(t):
    div()
    pad = (W - len(t) - 2) // 2
    print(" " * pad + f" {t} ")
    div()

div()
print(" " * 15 + "PATENT INTELLIGENCE REPORT")
div()
print(f"  Total Patents   : {int(total_patents):>12,}")
print(f"  Total Inventors : {int(total_inventors):>12,}")
print(f"  Total Companies : {int(total_companies):>12,}")
div()

sec("TOP 10 INVENTORS")
for i, row in top_inventors.iterrows():
    country = row["country"] if pd.notna(row["country"]) else "N/A"
    print(f"  {i+1:>2}. {row['inventor']:<32} {int(row['patents']):>6,}  [{country}]")

sec("TOP 10 COMPANIES")
for i, row in top_companies.iterrows():
    country = row["country"] if pd.notna(row["country"]) else "N/A"
    print(f"  {i+1:>2}. {row['company']:<32} {int(row['patents']):>6,}  [{country}]")

sec("TOP 15 COUNTRIES")
for i, row in top_countries.iterrows():
    print(f"  {i+1:>2}. {str(row['country']):<10} "
          f"{int(row['total_patents']):>8,} patents  "
          f"({float(row['share_pct']):.2f}%)")

sec("PATENTS PER YEAR  (1990-2024)")
max_p = int(yearly_trends["total_patents"].max())
for _, row in yearly_trends.iterrows():
    bar_len = int(30 * int(row["total_patents"]) / max_p)
    bar = "#" * bar_len
    print(f"  {int(row['year'])}  {bar:<30}  {int(row['total_patents']):,}")

sec("TOP 10 PATENT CATEGORIES (USPC)")
for i, row in top_categories.iterrows():
    print(f"  {i+1:>2}. Class {str(row['mainclass_id']):<12} "
          f"{int(row['patents']):>8,} patents")

sec("INVENTOR RANKINGS  (window functions)")
print(f"  {'Rank':<5} {'Inventor':<30} {'Country':<8} "
      f"{'Patents':>7}  {'In Country':>10}")
div("-")
for _, row in inventor_ranking.iterrows():
    country = str(row["country"]) if pd.notna(row["country"]) else "N/A"
    print(f"  {int(row['global_rank']):<5} {str(row['inventor']):<30} "
          f"{country:<8} {int(row['patents']):>7,}  "
          f"{int(row['rank_in_country']):>10}")

div()
print(f"  Reports saved to  -->  {REPORTS_DIR}")
div()
print()


# ══════════════════════════════════════════════════════════════════════════════
# B. CSV EXPORTS
# ══════════════════════════════════════════════════════════════════════════════
def save_csv(df, name):
    path = os.path.join(REPORTS_DIR, name)
    df.to_csv(path, index=False)
    print(f"  [CSV] {name}")

print("Saving CSV reports ...")
save_csv(top_inventors,    "top_inventors.csv")
save_csv(top_companies,    "top_companies.csv")
save_csv(top_countries,    "country_trends.csv")
save_csv(yearly_trends,    "yearly_trends.csv")
save_csv(top_categories,   "top_categories.csv")
save_csv(inventor_ranking, "inventor_ranking.csv")


# ══════════════════════════════════════════════════════════════════════════════
# C. JSON REPORT
# ══════════════════════════════════════════════════════════════════════════════
report = {
    "summary": {
        "total_patents":   int(total_patents),
        "total_inventors": int(total_inventors),
        "total_companies": int(total_companies),
    },
    "top_inventors": [
        {
            "rank":    i + 1,
            "name":    str(row["inventor"]),
            "country": str(row["country"]) if pd.notna(row["country"]) else None,
            "patents": int(row["patents"]),
        }
        for i, row in top_inventors.iterrows()
    ],
    "top_companies": [
        {
            "rank":    i + 1,
            "name":    str(row["company"]),
            "country": str(row["country"]) if pd.notna(row["country"]) else None,
            "patents": int(row["patents"]),
        }
        for i, row in top_companies.iterrows()
    ],
    "top_countries": [
        {
            "country":         str(row["country"]),
            "total_patents":   int(row["total_patents"]),
            "total_inventors": int(row["total_inventors"]),
            "share_pct":       float(row["share_pct"]),
        }
        for _, row in top_countries.iterrows()
    ],
    "yearly_trends": [
        {"year": int(row["year"]), "total_patents": int(row["total_patents"])}
        for _, row in yearly_trends.iterrows()
    ],
    "top_categories": [
        {"mainclass_id": str(row["mainclass_id"]),
         "patents":      int(row["patents"])}
        for _, row in top_categories.iterrows()
    ],
}

json_path = os.path.join(REPORTS_DIR, "patent_report.json")
with open(json_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"  [JSON] patent_report.json")


# ══════════════════════════════════════════════════════════════════════════════
# D. CHARTS
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating charts ...")

DARK = {
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#0f1117",
    "axes.edgecolor":   "#444",
    "axes.labelcolor":  "#ccc",
    "xtick.color":      "#ccc",
    "ytick.color":      "#ccc",
    "text.color":       "#eee",
    "grid.color":       "#2a2a2a",
    "grid.linestyle":   "--",
}
plt.rcParams.update(DARK)
BLUE   = "#4e9af1"
ORANGE = "#f1a94e"


def savefig(name):
    path = os.path.join(REPORTS_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [PNG] {name}")


# Chart 1 — Top 10 Inventors
fig, ax = plt.subplots(figsize=(10, 6))
df = top_inventors.sort_values("patents")
bars = ax.barh(df["inventor"], df["patents"].astype(int), color=BLUE)
ax.bar_label(bars, fmt="%,.0f", padding=4, color="#eee", fontsize=9)
ax.set_xlabel("Patents")
ax.set_title("Top 10 Inventors by Patent Count", fontsize=14, pad=12)
ax.xaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.grid(axis="x")
plt.tight_layout()
savefig("chart_top_inventors.png")

# Chart 2 — Top 10 Companies
fig, ax = plt.subplots(figsize=(10, 6))
df = top_companies.sort_values("patents")
bars = ax.barh(df["company"], df["patents"].astype(int), color=ORANGE)
ax.bar_label(bars, fmt="%,.0f", padding=4, color="#eee", fontsize=9)
ax.set_xlabel("Patents")
ax.set_title("Top 10 Companies by Patent Count", fontsize=14, pad=12)
ax.xaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.grid(axis="x")
plt.tight_layout()
savefig("chart_top_companies.png")

# Chart 3 — Patents Per Year
fig, ax = plt.subplots(figsize=(12, 5))
years  = yearly_trends["year"].astype(int)
totals = yearly_trends["total_patents"].astype(int)
ax.plot(years, totals, color=BLUE, linewidth=2.5, marker="o", markersize=4)
ax.fill_between(years, totals, alpha=0.15, color=BLUE)
ax.set_xlabel("Year")
ax.set_ylabel("Patents Granted")
ax.set_title("Patent Grants Per Year (1990-2024)", fontsize=14, pad=12)
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.grid(axis="y")
plt.tight_layout()
savefig("chart_yearly_trends.png")

# Chart 4 — Top 15 Countries
fig, ax = plt.subplots(figsize=(12, 6))
df = top_countries.head(15)
bars = ax.bar(df["country"].astype(str),
              df["total_patents"].astype(int), color=BLUE)
ax.bar_label(bars, fmt="%,.0f", padding=3, color="#eee", fontsize=8)
ax.set_xlabel("Country")
ax.set_ylabel("Patents")
ax.set_title("Top 15 Countries by Patent Count", fontsize=14, pad=12)
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.xticks(rotation=35, ha="right")
ax.grid(axis="y")
plt.tight_layout()
savefig("chart_top_countries.png")

# Chart 5 — Top 10 USPC Categories (pie)
fig, ax = plt.subplots(figsize=(8, 8))
df = top_categories.head(10)
wedges, texts, autotexts = ax.pie(
    df["patents"].astype(int),
    labels=df["mainclass_id"].astype(str),
    autopct="%1.1f%%",
    startangle=140,
    colors=plt.cm.tab10.colors,
    pctdistance=0.82,
)
for t in autotexts:
    t.set_fontsize(8)
    t.set_color("#eee")
ax.set_title("Top 10 Patent Categories (USPC)", fontsize=14, pad=16)
plt.tight_layout()
savefig("chart_categories_pie.png")

con.close()
print(f"\n  All reports saved to  -->  {REPORTS_DIR}\n")
