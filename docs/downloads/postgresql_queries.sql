-- PHARMA ANALYTICS | Assignment queries
-- Engine: PostgreSQL. Restore data/pharma_1401_1404.sql first.
SET search_path TO pharma, public;
-- Scope: 1401 -> 1402, all companies and products.
-- Run each section independently; every query is read-only.
-- Q4/Q5 share one result; Q6/Q7 share one result to preserve ranking.
-- value = IRR; volume = reported units; *_pct = percentage.
-- Interactive filters are implemented separately in docs/queries.js.
-- Always-true default filter conditions are omitted here for readability.

-- ========================================================================
-- Q1 | Annual sales value and volume
-- Value: IRR at consumer price. Volume: reported units.
-- ========================================================================

SELECT
    year,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume,
    COUNT(DISTINCT irc) AS products,
    COUNT(*) AS source_rows,
    SUM(CASE WHEN sales_consumer_rial IS NULL THEN 1 ELSE 0 END) AS missing_value_rows,
    SUM(CASE WHEN units_sold IS NULL THEN 1 ELSE 0 END) AS missing_volume_rows,
    SUM(
        CASE WHEN atc_l1 IS NULL THEN 1 ELSE 0 END
    ) AS unknown_atc_rows
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
GROUP BY
    year
ORDER BY
    year;


-- ========================================================================
-- Q2 + Q3 | Year-over-year value and volume growth
-- Growth is NULL when the baseline is zero or negative.
-- ========================================================================

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
    AND target.year = 1402;


-- ========================================================================
-- Q4 + Q5 | Top 10 suppliers
-- Rank by 1402 VALUE; keep this order for volume. Absent baseline = 0.
-- ========================================================================

WITH annual AS (
    SELECT
        supplier_id AS id,
        supplier_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM v_sales_dashboard
    WHERE year IN (1401, 1402)
        AND supplier_id IS NOT NULL
    GROUP BY
        supplier_id,
        supplier_name,
        year
),
leaders AS (
    SELECT
        *
    FROM annual
    WHERE year = 1402
    ORDER BY
        value DESC,
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
    t.value DESC,
    t.id;


-- ========================================================================
-- Q6 + Q7 | Top 10 distributors
-- Rank by 1402 VOLUME; keep this order for value. Absent baseline = 0.
-- ========================================================================

WITH annual AS (
    SELECT
        distributor_id AS id,
        distributor_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM v_sales_dashboard
    WHERE year IN (1401, 1402)
        AND distributor_id IS NOT NULL
    GROUP BY
        distributor_id,
        distributor_name,
        year
),
leaders AS (
    SELECT
        *
    FROM annual
    WHERE year = 1402
    ORDER BY
        volume DESC,
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
    t.volume DESC,
    t.id;


-- ========================================================================
-- Q8 | Sales by ATC Level 1
-- '?' retains unclassified sales for reconciliation to market totals.
-- ========================================================================

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
    year;


-- ========================================================================
-- Q9 | ATC share of annual market sales
-- Includes unclassified sales. Dashboard display uses valid ATC only.
-- ========================================================================

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
    category;


-- ========================================================================
-- Q10 | OTC versus prescription sales
-- Unknown status is retained; it is never assumed to be Rx.
-- ========================================================================

WITH classified AS (
    SELECT
        year,
        CASE
            WHEN is_otc = TRUE THEN 'OTC'
            WHEN is_otc = FALSE THEN 'Rx'
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
    year;


-- ========================================================================
-- APPENDIX | Supplier portfolio
-- Optional explorer input: aggregate before choosing period and ranking.
-- ========================================================================

SELECT
    supplier_id AS id,
    supplier_name AS name,
    year,
    COALESCE(atc_l1, '?') AS category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
    AND supplier_id IS NOT NULL
GROUP BY
    supplier_id,
    supplier_name,
    year,
    COALESCE(atc_l1, '?');


-- ========================================================================
-- APPENDIX | Distributor portfolio
-- Optional explorer input: aggregate before choosing period and ranking.
-- ========================================================================

SELECT
    distributor_id AS id,
    distributor_name AS name,
    year,
    COALESCE(atc_l1, '?') AS category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM v_sales_dashboard
WHERE year IN (1401, 1402)
    AND distributor_id IS NOT NULL
GROUP BY
    distributor_id,
    distributor_name,
    year,
    COALESCE(atc_l1, '?');


-- ========================================================================
-- APPENDIX | Domestic versus imported
-- Optional breakdown by origin.
-- ========================================================================

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
    year;
