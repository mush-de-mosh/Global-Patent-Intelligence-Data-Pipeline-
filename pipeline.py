"""
Global Patent Intelligence -- Data Pipeline
============================================
Stage 1 : Ingest raw TSV files in 100 000-row chunks
Stage 2 : Clean with pandas (nulls, dates, whitespace, dedup)
Stage 3 : Export clean CSVs  -->  data/
Stage 4 : Load SQLite DB     -->  patents.db  (via schema.sql)

Memory strategy
---------------
- All large tables are written to SQLite chunk-by-chunk (never fully in RAM)
- Temp files are redirected to D: which has ~83 GB free
- Only small lookup tables (locations, co_index dict) are held in RAM

Run:
    python pipeline.py
"""

import os
import tempfile
import sqlite3
import pandas as pd

# ── redirect temp files to D: (C: has almost no free space) ──────────────────
tempfile.tempdir = "D:\\tmp_pipeline"
os.makedirs(tempfile.tempdir, exist_ok=True)
os.environ["TMPDIR"]   = tempfile.tempdir
os.environ["TEMP"]     = tempfile.tempdir
os.environ["TMP"]      = tempfile.tempdir

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "dataset")
DB_PATH   = os.path.join(BASE_DIR, "patents.db")
CLEAN_DIR = os.path.join(BASE_DIR, "data")
CHUNK     = 100_000   # 100 000 rows per chunk

os.makedirs(CLEAN_DIR, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def tsv_chunks(filename, cols):
    """Yield cleaned chunks from a TSV file."""
    path = os.path.join(DATA_DIR, filename)
    for chunk in pd.read_csv(
        path, sep="\t", usecols=cols, dtype=str,
        chunksize=CHUNK, low_memory=False, on_bad_lines="skip"
    ):
        chunk.columns = chunk.columns.str.strip()
        for c in chunk.select_dtypes(include=["object"]).columns:
            chunk[c] = chunk[c].str.strip()
        yield chunk


def stream_to_db(filename, cols, table, con, transform=None):
    """Stream a TSV directly into a SQLite table chunk-by-chunk."""
    total = 0
    first = True
    for chunk in tsv_chunks(filename, cols):
        if transform:
            chunk = transform(chunk)
        if chunk is None or len(chunk) == 0:
            continue
        chunk.to_sql(table, con, if_exists="replace" if first else "append",
                     index=False)
        total += len(chunk)
        first = False
    print(f"  [DB]  {table:<22}  {total:>10,} rows")
    return total


def save_clean_csv(table, con, name, limit=None):
    """Export a DB table to a clean CSV file."""
    sql = f"SELECT * FROM {table}"
    if limit:
        sql += f" LIMIT {limit}"
    df = pd.read_sql(sql, con)
    path = os.path.join(CLEAN_DIR, f"clean_{name}.csv")
    df.to_csv(path, index=False)
    print(f"  [CSV] clean_{name}.csv  ({len(df):,} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# Open DB and apply schema
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*58)
print("  STAGE 1-4 -- INGEST, CLEAN & LOAD DATABASE")
print("="*58)

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA journal_mode=WAL")
con.execute("PRAGMA synchronous=NORMAL")
con.execute("PRAGMA temp_store=FILE")
con.execute(f"PRAGMA temp_store_directory='{tempfile.tempdir}'")

with open(os.path.join(BASE_DIR, "schema.sql")) as f:
    con.executescript(f.read())


# ── [1/6] locations (small lookup -- load fully into RAM) ────────────────────
print("\n  [1/6] locations (lookup table) ...")
loc_chunks = []
for chunk in tsv_chunks("g_location_disambiguated.tsv",
                        ["location_id", "disambig_city",
                         "disambig_state", "disambig_country"]):
    loc_chunks.append(chunk)
loc = pd.concat(loc_chunks, ignore_index=True)
loc = loc.rename(columns={
    "disambig_city":    "city",
    "disambig_state":   "state",
    "disambig_country": "country"
})
del loc_chunks
# Build fast dict lookups
loc_city    = loc.set_index("location_id")["city"].to_dict()
loc_state   = loc.set_index("location_id")["state"].to_dict()
loc_country = loc.set_index("location_id")["country"].to_dict()
del loc
print(f"       location lookup ready")


# ── [2/6] patents ─────────────────────────────────────────────────────────────
print("\n  [2/6] patents ...")

# load filing dates into a dict (small enough: one date per patent)
filing = {}
for chunk in tsv_chunks("g_application.tsv", ["patent_id", "filing_date"]):
    chunk["filing_date"] = pd.to_datetime(chunk["filing_date"],
                                          errors="coerce")
    chunk = chunk.dropna(subset=["patent_id", "filing_date"])
    chunk = chunk.sort_values("filing_date").drop_duplicates("patent_id")
    for _, row in chunk.iterrows():
        if row["patent_id"] not in filing:
            filing[row["patent_id"]] = row["filing_date"].strftime("%Y-%m-%d")

total_patents = 0
seen_patents  = set()
first = True
for chunk in tsv_chunks("g_patent.tsv",
                        ["patent_id", "patent_title", "patent_date"]):
    chunk = chunk.dropna(subset=["patent_id"])
    chunk = chunk[~chunk["patent_id"].isin(seen_patents)]
    chunk = chunk.drop_duplicates("patent_id")
    seen_patents.update(chunk["patent_id"].tolist())

    chunk["patent_date"] = pd.to_datetime(chunk["patent_date"],
                                          errors="coerce")
    chunk["year"]        = chunk["patent_date"].dt.year.astype("Int64")
    chunk["grant_date"]  = chunk["patent_date"].dt.strftime("%Y-%m-%d")
    chunk["filing_date"] = chunk["patent_id"].map(filing)
    chunk = chunk.rename(columns={"patent_title": "title"})
    chunk = chunk[["patent_id", "title", "filing_date", "grant_date", "year"]]

    chunk.to_sql("patents", con,
                 if_exists="replace" if first else "append", index=False)
    total_patents += len(chunk)
    first = False

del filing, seen_patents
print(f"       {total_patents:,} patents")


# ── [3/6] inventors ───────────────────────────────────────────────────────────
print("\n  [3/6] inventors ...")
seen_inv = set()
total_inv = 0
first = True
for chunk in tsv_chunks("g_inventor_disambiguated.tsv",
                        ["inventor_id", "disambig_inventor_name_first",
                         "disambig_inventor_name_last", "location_id"]):
    chunk["name"] = (
        chunk["disambig_inventor_name_first"].fillna("") + " " +
        chunk["disambig_inventor_name_last"].fillna("")
    ).str.strip()
    chunk = chunk.drop(columns=["disambig_inventor_name_first",
                                 "disambig_inventor_name_last"])
    chunk["city"]    = chunk["location_id"].map(loc_city)
    chunk["state"]   = chunk["location_id"].map(loc_state)
    chunk["country"] = chunk["location_id"].map(loc_country)
    chunk = chunk.drop(columns=["location_id"])
    chunk = chunk[~chunk["inventor_id"].isin(seen_inv)]
    chunk = chunk.drop_duplicates("inventor_id")
    chunk = chunk[chunk["name"] != ""]
    chunk = chunk.dropna(subset=["inventor_id"])
    chunk = chunk[["inventor_id", "name", "city", "state", "country"]]
    seen_inv.update(chunk["inventor_id"].tolist())
    chunk.to_sql("inventors", con,
                 if_exists="replace" if first else "append", index=False)
    total_inv += len(chunk)
    first = False

del seen_inv
print(f"       {total_inv:,} inventors")


# ── [4/6] companies + build co_index dict ────────────────────────────────────
print("\n  [4/6] companies ...")
seen_co  = set()
total_co = 0
co_index = {}   # patent_id -> [company_id, ...]  for patent_links
first = True
for chunk in tsv_chunks("g_assignee_disambiguated.tsv",
                        ["patent_id", "assignee_id",
                         "disambig_assignee_organization",
                         "disambig_assignee_individual_name_first",
                         "disambig_assignee_individual_name_last",
                         "assignee_type", "location_id"]):
    # collect patent->company links
    for _, row in chunk[["patent_id", "assignee_id"]].dropna().iterrows():
        co_index.setdefault(row["patent_id"], [])
        if row["assignee_id"] not in co_index[row["patent_id"]]:
            co_index[row["patent_id"]].append(row["assignee_id"])

    # build company rows
    chunk["name"] = chunk["disambig_assignee_organization"].fillna("").str.strip()
    mask = chunk["name"] == ""
    chunk.loc[mask, "name"] = (
        chunk.loc[mask, "disambig_assignee_individual_name_first"].fillna("") +
        " " +
        chunk.loc[mask, "disambig_assignee_individual_name_last"].fillna("")
    ).str.strip()
    chunk["city"]    = chunk["location_id"].map(loc_city)
    chunk["state"]   = chunk["location_id"].map(loc_state)
    chunk["country"] = chunk["location_id"].map(loc_country)
    chunk = chunk.drop(columns=["disambig_assignee_organization",
                                 "disambig_assignee_individual_name_first",
                                 "disambig_assignee_individual_name_last",
                                 "location_id", "patent_id"])
    chunk = chunk.rename(columns={"assignee_id":   "company_id",
                                   "assignee_type": "type"})
    chunk = chunk[~chunk["company_id"].isin(seen_co)]
    chunk = chunk.drop_duplicates("company_id")
    chunk = chunk[chunk["name"] != ""].dropna(subset=["company_id"])
    chunk = chunk[["company_id", "name", "type", "city", "state", "country"]]
    seen_co.update(chunk["company_id"].tolist())
    chunk.to_sql("companies", con,
                 if_exists="replace" if first else "append", index=False)
    total_co += len(chunk)
    first = False

del seen_co
print(f"       {total_co:,} companies")
print(f"       co_index covers {len(co_index):,} patents")


# ── [5/6] patent_links ────────────────────────────────────────────────────────
print("\n  [5/6] patent_links (streaming) ...")
total_links = 0
first = True
for chunk in tsv_chunks("g_inventor_disambiguated.tsv",
                        ["patent_id", "inventor_id"]):
    chunk = chunk.dropna()
    # map each patent to its list of company_ids, then explode
    chunk["company_id"] = chunk["patent_id"].map(co_index)
    chunk = chunk.explode("company_id")
    chunk = chunk[["patent_id", "inventor_id", "company_id"]]
    chunk.to_sql("patent_links", con,
                 if_exists="replace" if first else "append", index=False)
    total_links += len(chunk)
    first = False

del co_index
print(f"       {total_links:,} relationship rows")


# ── [6/6] supporting tables ───────────────────────────────────────────────────
print("\n  [6/6] classifications + citations ...")

total_cls = 0
first = True
for chunk in tsv_chunks("g_uspc_at_issue.tsv",
                        ["patent_id", "uspc_mainclass_id", "uspc_subclass_id"]):
    chunk = chunk.rename(columns={"uspc_mainclass_id": "mainclass_id",
                                   "uspc_subclass_id":  "subclass_id"})
    chunk.to_sql("classifications", con,
                 if_exists="replace" if first else "append", index=False)
    total_cls += len(chunk)
    first = False
print(f"  [DB]  classifications         {total_cls:>10,} rows")

total_cit = 0
first = True
cit_path = os.path.join(DATA_DIR, "g_us_patent_citation.tsv")
for chunk in pd.read_csv(
    cit_path, sep="\t",
    usecols=["patent_id", "citation_patent_id", "citation_category"],
    dtype=str, chunksize=CHUNK, engine="python", on_bad_lines="skip"
):
    chunk = chunk.rename(columns={"citation_category": "category"})
    chunk.to_sql("citations", con,
                 if_exists="replace" if first else "append", index=False)
    total_cit += len(chunk)
    first = False
print(f"  [DB]  citations               {total_cit:>10,} rows")

con.commit()


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 -- EXPORT CLEAN CSVs  (read back from DB -- already clean)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*58)
print("  STAGE 3 -- EXPORT CLEAN CSVs  -->  data/")
print("="*58 + "\n")

save_clean_csv("patents",   con, "patents")
save_clean_csv("inventors", con, "inventors")
save_clean_csv("companies", con, "companies")

con.close()

print("\n" + "="*58)
print("  Pipeline complete.")
print(f"  Database  -->  {DB_PATH}")
print(f"  Clean CSV -->  {CLEAN_DIR}")
print("  Next step -->  python reports.py")
print("="*58 + "\n")
