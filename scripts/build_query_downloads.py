"""Build readable, standalone SQL downloads for the default assignment scope."""
from pathlib import Path
from textwrap import dedent
ROOT = Path(__file__).resolve().parents[1]

def section(title, note, sql):
    return f"-- {'=' * 72}\n-- {title}\n-- {note}\n-- {'=' * 72}\n\n" + dedent(sql).strip() + ';\n'

def company(role, metric):
    return f'''WITH annual AS (
    SELECT
        {role}_id AS id,
        {role}_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM v_sales_dashboard
    WHERE year IN (1401, 1402)
        AND {role}_id IS NOT NULL
    GROUP BY
        {role}_id,
        {role}_name,
        year
),
leaders AS (
    SELECT
        *
    FROM annual
    WHERE year = 1402
    ORDER BY
        {metric} DESC,
        id
    LIMIT 10
)
SELECT
    t.id,
    t.name,
    t.value AS value_target,
    t.volume AS volume_target,
    CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_base,
    CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_base,
    t.value - CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_change,
    t.volume - CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_change
FROM leaders AS t
LEFT JOIN annual AS b
    ON b.id = t.id
    AND b.year = 1401
ORDER BY
    t.{metric} DESC,
    t.id'''

def build():
    sections=[]
    sections.append(section('Q1 | Annual sales value and volume', 'Value: IRR at consumer price. Volume: reported units.', '''
SELECT
    year,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume,
    COUNT(DISTINCT irc) AS products,
    SUM(source_rows) AS source_rows,
    SUM(missing_value_rows) AS missing_value_rows,
    SUM(missing_volume_rows) AS missing_volume_rows,
    SUM(
        CASE WHEN atc_l1 IS NULL THEN source_rows ELSE 0 END
    ) AS unknown_atc_rows
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
GROUP BY
    year
ORDER BY
    year
'''))
    sections.append(section('Q2 + Q3 | Year-over-year value and volume growth', 'Growth is NULL when the baseline is zero or negative.', '''
WITH annual AS (
    SELECT
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM fact_sales
    WHERE year IN (1401, 1402)
    GROUP BY
        year
)
SELECT
    100.0 * (target.value - base.value)
    / NULLIF(
        CASE WHEN base.value > 0 THEN base.value END,
        0
    ) AS value_growth_pct,

    100.0 * (target.volume - base.volume)
    / NULLIF(
        CASE WHEN base.volume > 0 THEN base.volume END,
        0
    ) AS volume_growth_pct
FROM annual AS base
JOIN annual AS target
    ON base.year = 1401
    AND target.year = 1402
'''))
    sections.append(section('Q4 + Q5 | Top 10 suppliers', 'Rank by 1402 VALUE; keep this order for volume. Absent baseline = 0.',company('supplier','value')))
    sections.append(section('Q6 + Q7 | Top 10 distributors', 'Rank by 1402 VOLUME; keep this order for value. Absent baseline = 0.',company('distributor','volume')))
    sections.append(section('Q8 | Sales by ATC Level 1', "'?' retains unclassified sales for reconciliation to market totals.", '''
SELECT
    year,
    COALESCE(atc_l1, '?') AS category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
GROUP BY
    year,
    COALESCE(atc_l1, '?')
ORDER BY
    category,
    year
'''))
    sections.append(section('Q9 | ATC share of annual market sales', 'Includes unclassified sales. Dashboard display uses valid ATC only.', '''
WITH groups AS (
    SELECT
        year,
        COALESCE(atc_l1, '?') AS category,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM v_sales_dashboard
    WHERE year IN (1401, 1402)
    GROUP BY
        year,
        COALESCE(atc_l1, '?')
)
SELECT
    *,

    100.0 * value
    / NULLIF(
        SUM(value) OVER (
            PARTITION BY year
        ),
        0
    ) AS value_share_pct,

    100.0 * volume
    / NULLIF(
        SUM(volume) OVER (
            PARTITION BY year
        ),
        0
    ) AS volume_share_pct
FROM groups
ORDER BY
    year,
    category
'''))
    sections.append(section('Q10 | OTC versus prescription sales', 'Unknown status is retained; it is never assumed to be Rx.', '''
WITH classified AS (
    SELECT
        year,
        CASE
            WHEN is_otc = 1 THEN 'OTC'
            WHEN is_otc = 0 THEN 'Rx'
            ELSE 'Unknown'
        END AS category,
        sales_consumer_rial,
        units_sold
    FROM v_sales_dashboard
    WHERE year IN (1401, 1402)
)
SELECT
    year,
    category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM classified
GROUP BY
    year,
    category
ORDER BY
    category,
    year
'''))
    for role in ['supplier','distributor']:
        sections.append(section('APPENDIX | '+role.title()+' portfolio', 'Optional explorer input: aggregate before choosing period and ranking.', f'''
SELECT
    {role}_id AS id,
    {role}_name AS name,
    year,
    COALESCE(atc_l1, '?') AS category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
    AND {role}_id IS NOT NULL
GROUP BY
    {role}_id,
    {role}_name,
    year,
    COALESCE(atc_l1, '?')
'''))
    sections.append(section('APPENDIX | Domestic versus imported', 'Optional breakdown by origin.', '''
SELECT
    year,
    COALESCE(origin, 'نامشخص') AS category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
GROUP BY
    year,
    COALESCE(origin, 'نامشخص')
ORDER BY
    category,
    year
'''))
    header='''-- PHARMA ANALYTICS | Assignment queries
-- Engine: SQLite. Open docs/data/dashboard.sqlite before running.
-- Scope: 1401 -> 1402, all companies and products.
-- Run each section independently; every query is read-only.
-- Q4/Q5 share one result; Q6/Q7 share one result to preserve ranking.
-- value = IRR; volume = reported units; *_pct = percentage.
-- Interactive filters are implemented separately in docs/queries.js.
-- Always-true default filter conditions are omitted here for readability.

'''
    text=header+'\n\n'.join(sections)
    (ROOT/'sql/analytical_queries.sql').write_text(text,encoding='utf-8')
    pg=text.replace('-- Engine: SQLite. Open docs/data/dashboard.sqlite before running.', '-- Engine: PostgreSQL. Restore data/pharma_1401_1404.sql first.\nSET search_path TO pharma, public;')
    pg=pg.replace('SUM(source_rows)','COUNT(*)').replace('SUM(missing_value_rows)','SUM(CASE WHEN sales_consumer_rial IS NULL THEN 1 ELSE 0 END)').replace('SUM(missing_volume_rows)','SUM(CASE WHEN units_sold IS NULL THEN 1 ELSE 0 END)').replace('THEN source_rows ELSE 0','THEN 1 ELSE 0').replace('is_otc = 1','is_otc = TRUE').replace('is_otc = 0','is_otc = FALSE')
    from build_postgresql_assignment import build_postgresql
    build_postgresql(sections)
    print('Generated readable SQLite and PostgreSQL query files.')

if __name__=='__main__':
    build()
