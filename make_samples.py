import sqlite3, csv, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
con = sqlite3.connect(os.path.join(BASE_DIR, "patents.db"))

for table, fname in [
    ("patents",   "sample_patents"),
    ("inventors", "sample_inventors"),
    ("companies", "sample_companies"),
]:
    cur  = con.execute(f"SELECT * FROM {table} LIMIT 1000")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    path = os.path.join(BASE_DIR, "data", f"{fname}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"  {fname}.csv  ({len(rows)} rows)  -->  {path}")

con.close()
print("Done.")
