import sqlite3
import csv
import os

DB_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patents.db")
CLEAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(CLEAN_DIR, exist_ok=True)

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row

for table in ["inventors", "companies"]:
    path = os.path.join(CLEAN_DIR, f"clean_{table}.csv")
    cur  = con.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    total = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        while True:
            rows = cur.fetchmany(100_000)
            if not rows:
                break
            writer.writerows(rows)
            total += len(rows)
    print(f"  clean_{table}.csv  ({total:,} rows)  -->  {path}")

con.close()
print("Done.")
