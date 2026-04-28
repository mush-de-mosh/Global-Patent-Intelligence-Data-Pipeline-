-- Global Patent Intelligence - Analysis Queries
-- Run against: patents.db


-- Q1: Top Inventors
SELECT
    i.name                          AS inventor,
    i.country,
    COUNT(DISTINCT pl.patent_id)    AS total_patents
FROM   patent_links pl
JOIN   inventors    i  ON pl.inventor_id = i.inventor_id
WHERE  i.name != ''
GROUP  BY i.inventor_id
ORDER  BY total_patents DESC
LIMIT  15;


-- Q2: Top Companies
SELECT
    c.name                          AS company,
    c.country,
    c.type,
    COUNT(DISTINCT pl.patent_id)    AS total_patents
FROM   patent_links pl
JOIN   companies    c  ON pl.company_id = c.company_id
WHERE  c.name IS NOT NULL
GROUP  BY c.company_id
ORDER  BY total_patents DESC
LIMIT  15;


-- Q3: Countries
SELECT
    i.country,
    COUNT(DISTINCT pl.patent_id)    AS total_patents,
    COUNT(DISTINCT pl.inventor_id)  AS total_inventors,
    ROUND(
        100.0 * COUNT(DISTINCT pl.patent_id) /
        (SELECT COUNT(DISTINCT patent_id) FROM patent_links), 4
    )                               AS share_pct
FROM   patent_links pl
JOIN   inventors    i  ON pl.inventor_id = i.inventor_id
WHERE  i.country IS NOT NULL
GROUP  BY i.country
ORDER  BY total_patents DESC
LIMIT  20;


-- Q4: Trends Over Time
SELECT
    year,
    COUNT(*)                        AS total_patents,
    COUNT(*) - LAG(COUNT(*)) OVER (
        ORDER BY year
    )                               AS yoy_change
FROM   patents
WHERE  year IS NOT NULL
  AND  year BETWEEN 1990 AND 2024
GROUP  BY year
ORDER  BY year;


-- Q5: JOIN - patents with inventors and companies
SELECT
    p.patent_id,
    p.title,
    p.year,
    p.filing_date,
    i.name          AS inventor,
    i.country       AS inventor_country,
    c.name          AS company,
    c.country       AS company_country
FROM   patents       p
JOIN   patent_links  pl ON p.patent_id    = pl.patent_id
JOIN   inventors     i  ON pl.inventor_id = i.inventor_id
JOIN   companies     c  ON pl.company_id  = c.company_id
WHERE  p.year IS NOT NULL
ORDER  BY p.year DESC, p.patent_id
LIMIT  50;


-- Q6: CTE - top company per country
WITH company_counts AS (
    SELECT
        c.company_id,
        c.name      AS company,
        c.country,
        COUNT(DISTINCT pl.patent_id) AS total_patents
    FROM   patent_links pl
    JOIN   companies    c  ON pl.company_id = c.company_id
    WHERE  c.country IS NOT NULL
      AND  c.name    IS NOT NULL
    GROUP  BY c.company_id
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY country
               ORDER BY total_patents DESC
           ) AS rank_in_country
    FROM   company_counts
)
SELECT
    country,
    company,
    total_patents
FROM   ranked
WHERE  rank_in_country = 1
ORDER  BY total_patents DESC
LIMIT  20;


-- Q7: Ranking with window functions
WITH inventor_counts AS (
    SELECT
        i.inventor_id,
        i.name      AS inventor,
        i.country,
        COUNT(DISTINCT pl.patent_id) AS total_patents
    FROM   patent_links pl
    JOIN   inventors    i  ON pl.inventor_id = i.inventor_id
    WHERE  i.name    != ''
      AND  i.country IS NOT NULL
    GROUP  BY i.inventor_id
)
SELECT
    inventor,
    country,
    total_patents,
    RANK()  OVER (ORDER BY total_patents DESC)                       AS global_rank,
    RANK()  OVER (PARTITION BY country ORDER BY total_patents DESC)  AS rank_in_country,
    ROUND(
        100.0 * total_patents / SUM(total_patents) OVER (), 4
    )                                                                AS pct_of_all_patents
FROM   inventor_counts
ORDER  BY global_rank
LIMIT  30;
