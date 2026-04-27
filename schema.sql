-- ============================================================
--  Global Patent Intelligence -- Database Schema
--  Engine : SQLite 3
-- ============================================================

DROP TABLE IF EXISTS patent_links;
DROP TABLE IF EXISTS classifications;
DROP TABLE IF EXISTS citations;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS inventors;
DROP TABLE IF EXISTS patents;

-- ------------------------------------------------------------
-- patents
-- ------------------------------------------------------------
CREATE TABLE patents (
    patent_id   TEXT PRIMARY KEY,
    title       TEXT,
    filing_date TEXT,       -- YYYY-MM-DD (from g_application)
    grant_date  TEXT,       -- YYYY-MM-DD (from g_patent)
    year        INTEGER     -- grant year  (from g_patent)
);

-- ------------------------------------------------------------
-- inventors
-- ------------------------------------------------------------
CREATE TABLE inventors (
    inventor_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    country     TEXT
);

-- ------------------------------------------------------------
-- companies  (assignees)
-- ------------------------------------------------------------
CREATE TABLE companies (
    company_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT,
    city        TEXT,
    state       TEXT,
    country     TEXT
);

-- ------------------------------------------------------------
-- patent_links  (relationship table)
-- ------------------------------------------------------------
CREATE TABLE patent_links (
    patent_id   TEXT,
    inventor_id TEXT,
    company_id  TEXT,
    FOREIGN KEY (patent_id)   REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id),
    FOREIGN KEY (company_id)  REFERENCES companies(company_id)
);

-- ------------------------------------------------------------
-- classifications  (USPC codes)
-- ------------------------------------------------------------
CREATE TABLE classifications (
    patent_id    TEXT,
    mainclass_id TEXT,
    subclass_id  TEXT,
    FOREIGN KEY (patent_id) REFERENCES patents(patent_id)
);

-- ------------------------------------------------------------
-- citations
-- ------------------------------------------------------------
CREATE TABLE citations (
    patent_id          TEXT,
    citation_patent_id TEXT,
    category           TEXT,
    FOREIGN KEY (patent_id) REFERENCES patents(patent_id)
);

-- ------------------------------------------------------------
-- Indexes for fast JOINs and filters
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_links_patent   ON patent_links(patent_id);
CREATE INDEX IF NOT EXISTS idx_links_inventor ON patent_links(inventor_id);
CREATE INDEX IF NOT EXISTS idx_links_company  ON patent_links(company_id);
CREATE INDEX IF NOT EXISTS idx_patents_year   ON patents(year);
CREATE INDEX IF NOT EXISTS idx_inv_country    ON inventors(country);
CREATE INDEX IF NOT EXISTS idx_co_country     ON companies(country);
CREATE INDEX IF NOT EXISTS idx_class_patent   ON classifications(patent_id);
CREATE INDEX IF NOT EXISTS idx_cite_patent    ON citations(patent_id);
