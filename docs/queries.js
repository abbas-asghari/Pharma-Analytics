/* Shared SQL used by the browser worker and the validation script.
   Named parameters are bound, never interpolated from user input. */
const FILTER_SQL = `year IN (:base,:target)
 AND (:supplier = 0 OR supplier_id = :supplier)
 AND (:distributor = 0 OR distributor_id = :distributor)
 AND (:atc = '' OR COALESCE(atc_l1,'?') = :atc)
 AND (:otc = -1 OR COALESCE(is_otc,2) = :otc)
 AND (:origin = '' OR origin = :origin)
 AND (:search = '' OR irc LIKE :pattern OR generic_name LIKE :pattern
      OR brand_name_fa LIKE :pattern OR brand_name_en LIKE :pattern)`;
const BASE_SQL = `WITH filtered AS (SELECT * FROM v_sales_dashboard WHERE ${FILTER_SQL})`;
function companyQuery(role, metric) {
 return `${BASE_SQL}, annual AS (
 SELECT ${role}_id AS id,${role}_name AS name,year,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered WHERE ${role}_id IS NOT NULL GROUP BY ${role}_id,${role}_name,year
 ), leaders AS (SELECT * FROM annual WHERE year=:target ORDER BY ${metric} DESC,id LIMIT 10)
 SELECT t.id,t.name,t.value AS value_target,t.volume AS volume_target,
 CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_base,
 CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_base,
 t.value-CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_change,
 t.volume-CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_change
 FROM leaders t LEFT JOIN annual b ON b.id=t.id AND b.year=:base
 ORDER BY t.${metric} DESC,t.id`;
}
function explorerQuery(role){return `${BASE_SQL} SELECT ${role}_id AS id,${role}_name AS name,year,COALESCE(atc_l1,'?') AS category,SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume FROM filtered WHERE ${role}_id IS NOT NULL GROUP BY ${role}_id,${role}_name,year,COALESCE(atc_l1,'?')`;}
const QUERY_DEFS = {
 totals: `${BASE_SQL} SELECT year,SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume,
 COUNT(DISTINCT irc) AS products,SUM(source_rows) AS source_rows,
 SUM(missing_value_rows) AS missing_value_rows,SUM(missing_volume_rows) AS missing_volume_rows,
 SUM(CASE WHEN atc_l1 IS NULL THEN source_rows ELSE 0 END) AS unknown_atc_rows
 FROM filtered GROUP BY year ORDER BY year`,
 supplier_explorer: explorerQuery('supplier'),
 distributor_explorer: explorerQuery('distributor'),
 suppliers: companyQuery('supplier','value'),
 distributors: companyQuery('distributor','volume'),
 atc: `${BASE_SQL} SELECT year,COALESCE(atc_l1,'?') AS category,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered GROUP BY year,COALESCE(atc_l1,'?') ORDER BY category,year`,
 otc: `${BASE_SQL} SELECT year,CASE WHEN is_otc=1 THEN 'OTC' WHEN is_otc=0 THEN 'Rx' ELSE 'Unknown' END AS category,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered GROUP BY year,CASE WHEN is_otc=1 THEN 'OTC' WHEN is_otc=0 THEN 'Rx' ELSE 'Unknown' END ORDER BY category,year`,
 origin: `${BASE_SQL} SELECT year,COALESCE(origin,'نامشخص') AS category,
 SUM(sales_consumer_rial) AS value,SUM(units_sold) AS volume
 FROM filtered GROUP BY year,COALESCE(origin,'نامشخص') ORDER BY category,year`
};
if(typeof module !== 'undefined') module.exports={QUERY_DEFS,FILTER_SQL};
