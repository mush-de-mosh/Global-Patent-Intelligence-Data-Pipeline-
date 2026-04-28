"""
Global Patent Intelligence - Streamlit Dashboard

Run: streamlit run dashboard.py
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "patents.db")

st.set_page_config(
    page_title="Patent Intelligence",
    page_icon="patent",
    layout="wide"
)


@st.cache_resource
def get_con():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA temp_store=FILE")
    con.execute("PRAGMA temp_store_directory='D:\\\\tmp_pipeline'")
    con.execute("PRAGMA cache_size=-65536")
    return con


@st.cache_data
def run(sql):
    return pd.read_sql(sql, get_con())


st.sidebar.title("Patent Intelligence")
page  = st.sidebar.radio(
    "Navigate",
    ["Overview", "Inventors", "Companies", "Countries", "Trends", "Categories"]
)
top_n = st.sidebar.slider("Top N results", 5, 30, 10)

BLUE   = "#4e9af1"
ORANGE = "#f1a94e"


def dark_fig(w=10, h=5):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")
    ax.tick_params(colors="#ccc")
    ax.xaxis.label.set_color("#ccc")
    ax.yaxis.label.set_color("#ccc")
    ax.title.set_color("#eee")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")
    return fig, ax


if page == "Overview":
    st.title("Global Patent Intelligence Dashboard")
    st.markdown("Real-world patent data from [PatentsView](https://patentsview.org)")

    total_p = run("SELECT COUNT(*) AS n FROM patents").iloc[0]["n"]
    total_i = run("SELECT COUNT(*) AS n FROM inventors").iloc[0]["n"]
    total_c = run("SELECT COUNT(*) AS n FROM companies").iloc[0]["n"]
    total_l = run("SELECT COUNT(*) AS n FROM patent_links").iloc[0]["n"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Patents",    f"{int(total_p):,}")
    c2.metric("Total Inventors",  f"{int(total_i):,}")
    c3.metric("Total Companies",  f"{int(total_c):,}")
    c4.metric("Relationship Rows", f"{int(total_l):,}")

    st.subheader("Patents Granted Per Year")
    yearly = run("""
        SELECT year, COUNT(*) AS total_patents
        FROM   patents
        WHERE  year BETWEEN 1990 AND 2024
        GROUP  BY year ORDER BY year
    """)
    fig, ax = dark_fig(12, 4)
    ax.plot(yearly["year"].astype(int), yearly["total_patents"].astype(int),
            color=BLUE, linewidth=2.5, marker="o", markersize=3)
    ax.fill_between(yearly["year"].astype(int),
                    yearly["total_patents"].astype(int),
                    alpha=0.15, color=BLUE)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", color="#2a2a2a", linestyle="--")
    st.pyplot(fig)
    plt.close()


elif page == "Inventors":
    st.title("Top Inventors")
    df = run(f"""
        SELECT i.name AS inventor, i.country,
               COUNT(DISTINCT pl.patent_id) AS patents
        FROM   patent_links pl
        JOIN   inventors i ON pl.inventor_id = i.inventor_id
        WHERE  i.name != ''
        GROUP  BY i.inventor_id
        ORDER  BY patents DESC
        LIMIT  {top_n}
    """)
    st.dataframe(df, use_container_width=True)

    fig, ax = dark_fig(10, max(4, top_n // 2))
    d = df.sort_values("patents")
    bars = ax.barh(d["inventor"], d["patents"].astype(int), color=BLUE)
    ax.bar_label(bars, fmt="%,.0f", padding=4, color="#eee", fontsize=8)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="x", color="#2a2a2a", linestyle="--")
    ax.set_xlabel("Patents", color="#ccc")
    ax.set_title(f"Top {top_n} Inventors", color="#eee")
    st.pyplot(fig)
    plt.close()


elif page == "Companies":
    st.title("Top Companies")
    df = run(f"""
        SELECT c.name AS company, c.country, c.type,
               COUNT(DISTINCT pl.patent_id) AS patents
        FROM   patent_links pl
        JOIN   companies c ON pl.company_id = c.company_id
        WHERE  c.name IS NOT NULL
        GROUP  BY c.company_id
        ORDER  BY patents DESC
        LIMIT  {top_n}
    """)
    st.dataframe(df, use_container_width=True)

    fig, ax = dark_fig(10, max(4, top_n // 2))
    d = df.sort_values("patents")
    bars = ax.barh(d["company"], d["patents"].astype(int), color=ORANGE)
    ax.bar_label(bars, fmt="%,.0f", padding=4, color="#eee", fontsize=8)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="x", color="#2a2a2a", linestyle="--")
    ax.set_xlabel("Patents", color="#ccc")
    ax.set_title(f"Top {top_n} Companies", color="#eee")
    st.pyplot(fig)
    plt.close()


elif page == "Countries":
    st.title("Patents by Country")
    df = run(f"""
        SELECT i.country,
               COUNT(DISTINCT pl.patent_id)   AS total_patents,
               COUNT(DISTINCT pl.inventor_id) AS total_inventors,
               ROUND(100.0 * COUNT(DISTINCT pl.patent_id) /
                   (SELECT COUNT(DISTINCT patent_id) FROM patent_links), 2
               ) AS share_pct
        FROM   patent_links pl
        JOIN   inventors i ON pl.inventor_id = i.inventor_id
        WHERE  i.country IS NOT NULL
        GROUP  BY i.country
        ORDER  BY total_patents DESC
        LIMIT  {top_n}
    """)
    st.dataframe(df, use_container_width=True)

    fig, ax = dark_fig(12, 5)
    bars = ax.bar(df["country"].astype(str),
                  df["total_patents"].astype(int), color=BLUE)
    ax.bar_label(bars, fmt="%,.0f", padding=3, color="#eee", fontsize=8)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    plt.xticks(rotation=35, ha="right", color="#ccc")
    ax.grid(axis="y", color="#2a2a2a", linestyle="--")
    ax.set_title(f"Top {top_n} Countries by Patent Count", color="#eee")
    st.pyplot(fig)
    plt.close()


elif page == "Trends":
    st.title("Patent Trends Over Time")
    year_min, year_max = st.slider("Year range", 1976, 2024, (1990, 2024))
    df = run(f"""
        SELECT year, COUNT(*) AS total_patents
        FROM   patents
        WHERE  year BETWEEN {year_min} AND {year_max}
        GROUP  BY year ORDER BY year
    """)
    st.dataframe(df, use_container_width=True)

    fig, ax = dark_fig(12, 5)
    ax.plot(df["year"].astype(int), df["total_patents"].astype(int),
            color=BLUE, linewidth=2.5, marker="o", markersize=4)
    ax.fill_between(df["year"].astype(int),
                    df["total_patents"].astype(int),
                    alpha=0.15, color=BLUE)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", color="#2a2a2a", linestyle="--")
    ax.set_xlabel("Year", color="#ccc")
    ax.set_ylabel("Patents Granted", color="#ccc")
    ax.set_title("Patents Granted Per Year", color="#eee")
    st.pyplot(fig)
    plt.close()


elif page == "Categories":
    st.title("Top Patent Categories (USPC)")
    df = run(f"""
        SELECT mainclass_id,
               COUNT(DISTINCT patent_id) AS patents
        FROM   classifications
        WHERE  mainclass_id IS NOT NULL
        GROUP  BY mainclass_id
        ORDER  BY patents DESC
        LIMIT  {top_n}
    """)
    st.dataframe(df, use_container_width=True)

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")
    wedges, texts, autotexts = ax.pie(
        df["patents"].astype(int),
        labels=df["mainclass_id"].astype(str),
        autopct="%1.1f%%",
        startangle=140,
        colors=plt.cm.tab10.colors,
        pctdistance=0.82,
    )
    for t in texts + autotexts:
        t.set_color("#eee")
        t.set_fontsize(9)
    ax.set_title(f"Top {top_n} Patent Categories", color="#eee", fontsize=14)
    st.pyplot(fig)
    plt.close()
