-- Run in SQLite on docs/data/dashboard.sqlite.
-- Real queries used by docs/worker.js.
-- Default: 1401 -> 1402; all companies/categories.

-- Q1. Annual sales value and volume
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')) SELECT year,SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume,
 COUNT(DISTINCT irc) AS products,SUM(source_rows) AS source_rows,
 SUM(missing_value_rows) AS missing_value_rows,SUM(missing_volume_rows) AS missing_volume_rows,
 SUM(CASE WHEN atc_l1 IS NULL THEN source_rows ELSE 0 END) AS unknown_atc_rows
 FROM filtered GROUP BY year ORDER BY year;

-- Optional. Supplier portfolio by year and ATC
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')) SELECT supplier_id AS id,supplier_name AS name,year,COALESCE(atc_l1,'?') AS category,SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume FROM filtered WHERE supplier_id IS NOT NULL GROUP BY supplier_id,supplier_name,year,COALESCE(atc_l1,'?');

-- Optional. Distributor portfolio by year and ATC
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')) SELECT distributor_id AS id,distributor_name AS name,year,COALESCE(atc_l1,'?') AS category,SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume FROM filtered WHERE distributor_id IS NOT NULL GROUP BY distributor_id,distributor_name,year,COALESCE(atc_l1,'?');

-- Q4 + Q5. Same top suppliers, ranked by target-year VALUE
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')), annual AS (
 SELECT supplier_id AS id,supplier_name AS name,year,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered WHERE supplier_id IS NOT NULL GROUP BY supplier_id,supplier_name,year
 ), leaders AS (SELECT * FROM annual WHERE year=1402 ORDER BY value DESC,id LIMIT 10)
 SELECT t.id,t.name,t.value AS value_target,t.volume AS volume_target,
 CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_base,
 CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_base,
 t.value-CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_change,
 t.volume-CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_change
 FROM leaders t LEFT JOIN annual b ON b.id=t.id AND b.year=1401
 ORDER BY t.value DESC,t.id;

-- Q6 + Q7. Same top distributors, ranked by target-year VOLUME
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')), annual AS (
 SELECT distributor_id AS id,distributor_name AS name,year,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered WHERE distributor_id IS NOT NULL GROUP BY distributor_id,distributor_name,year
 ), leaders AS (SELECT * FROM annual WHERE year=1402 ORDER BY volume DESC,id LIMIT 10)
 SELECT t.id,t.name,t.value AS value_target,t.volume AS volume_target,
 CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_base,
 CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_base,
 t.value-CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_change,
 t.volume-CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_change
 FROM leaders t LEFT JOIN annual b ON b.id=t.id AND b.year=1401
 ORDER BY t.volume DESC,t.id;

-- Q8. ATC L1 sales, including Unknown
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')) SELECT year,COALESCE(atc_l1,'?') AS category,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered GROUP BY year,COALESCE(atc_l1,'?') ORDER BY category,year;

-- Q10. OTC / Rx / Unknown
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')) SELECT year,CASE WHEN is_otc=1 THEN 'OTC' WHEN is_otc=0 THEN 'Rx' ELSE 'Unknown' END AS category,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered GROUP BY year,CASE WHEN is_otc=1 THEN 'OTC' WHEN is_otc=0 THEN 'Rx' ELSE 'Unknown' END ORDER BY category,year;

-- Optional. Domestic / imported
WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE year IN (1401,1402)
 AND (0 = 0 OR supplier_id = 0)
 AND (0 = 0 OR distributor_id = 0)
 AND ('' = '' OR COALESCE(atc_l1,'?') = '')
 AND (-1 = -1 OR COALESCE(is_otc,2) = -1)
 AND ('' = '' OR origin = '')
 AND ('' = '' OR irc LIKE '%%' OR generic_name LIKE '%%'
      OR brand_name_fa LIKE '%%' OR brand_name_en LIKE '%%')) SELECT year,COALESCE(origin,'Ù†Ø§Ù…Ø´Ø®Øµ') AS category,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered GROUP BY year,COALESCE(origin,'Ù†Ø§Ù…Ø´Ø®Øµ') ORDER BY category,year;

-- Q2 + Q3. Growth; baseline <= 0 is undefined (NULL).
WITH a AS (SELECT year,SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
FROM fact_sales WHERE year IN (1401,1402) GROUP BY year)
SELECT 100.0*(t.value-b.value)/NULLIF(CASE WHEN b.value>0 THEN b.value END,0) AS value_growth_pct,
100.0*(t.volume-b.volume)/NULLIF(CASE WHEN b.volume>0 THEN b.volume END,0) AS volume_growth_pct
FROM a b JOIN a t ON b.year=1401 AND t.year=1402;

-- Q9. Signed sales shares. A zero denominator produces NULL.
WITH groups AS (SELECT year,COALESCE(atc_l1,'?') AS category,
SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
FROM v_sales_dashboard WHERE year IN (1401,1402) GROUP BY year,COALESCE(atc_l1,'?'))
SELECT *,100.0*value/NULLIF(SUM(value) OVER(PARTITION BY year),0) AS value_share_pct,
100.0*volume/NULLIF(SUM(volume) OVER(PARTITION BY year),0) AS volume_share_pct
FROM groups ORDER BY year,category;
