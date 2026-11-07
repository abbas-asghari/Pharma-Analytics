-- PHARMA ANALYTICS | PostgreSQL | Questions 01-10
-- ابتدا فایل data/pharma_1401_1404.sql را در دیتابیس وارد کنید.
-- هر بخش را مستقل در Query Tool اجرا کنید؛ نام schema در کوئری‌ها مشخص است.
-- دامنه: سال‌های ۱۴۰۱ و ۱۴۰۲، همه شرکت‌ها و محصولات.
-- value: ریال | volume: واحد گزارش‌شده | growth_pct و share_pct: درصد
-- سؤال ۵ ترتیب سؤال ۴ و سؤال ۷ ترتیب سؤال ۶ را حفظ می‌کند.
-- سؤال‌های ۸ و ۹ گروه فاقد ATC را برای تطبیق با کل بازار حفظ می‌کنند.
-- نمودار سایت گروه فاقد ATC را نمایش نمی‌دهد و درصدها را بر اقلام دارای ATC محاسبه می‌کند.

-- ========================================================================
-- QUESTION 01 / 10 | Sales Volume / Sales Value per Year
-- سؤال ۱: مقایسه مجموع تعداد و مبلغ فروش سال‌های ۱۴۰۱ و ۱۴۰۲؛ مبلغ به ریال.
-- ========================================================================

SELECT
    year,
    SUM(units_sold) AS sales_volume,
    SUM(sales_consumer_rial) AS sales_value_rial
FROM pharma.fact_sales
WHERE year IN (1401, 1402)
GROUP BY
    year
ORDER BY
    year;


-- ========================================================================
-- QUESTION 02 / 10 | Sales Value Growth Rate (1401 -> 1402)
-- سؤال 2: نرخ رشد مبلغ فروش؛ خروجی درصد است. پایه صفر یا منفی: NULL.
-- ========================================================================

WITH annual AS (
    SELECT
        year,
        SUM(sales_consumer_rial) AS amount
    FROM pharma.fact_sales
    WHERE year IN (1401, 1402)
    GROUP BY
        year
)
SELECT
    base.amount AS sales_value_1401,
    target.amount AS sales_value_1402,
    target.amount - base.amount AS absolute_change,
    100.0 * (target.amount - base.amount)
    / NULLIF(
        CASE WHEN base.amount > 0 THEN base.amount END,
        0
    ) AS growth_pct
FROM annual AS base
JOIN annual AS target
    ON base.year = 1401
    AND target.year = 1402;


-- ========================================================================
-- QUESTION 03 / 10 | Sales Volume Growth Rate (1401 -> 1402)
-- سؤال 3: نرخ رشد تعداد فروش؛ خروجی درصد است. پایه صفر یا منفی: NULL.
-- ========================================================================

WITH annual AS (
    SELECT
        year,
        SUM(units_sold) AS amount
    FROM pharma.fact_sales
    WHERE year IN (1401, 1402)
    GROUP BY
        year
)
SELECT
    base.amount AS sales_volume_1401,
    target.amount AS sales_volume_1402,
    target.amount - base.amount AS absolute_change,
    100.0 * (target.amount - base.amount)
    / NULLIF(
        CASE WHEN base.amount > 0 THEN base.amount END,
        0
    ) AS growth_pct
FROM annual AS base
JOIN annual AS target
    ON base.year = 1401
    AND target.year = 1402;


-- ========================================================================
-- QUESTION 04 / 10 | Sales Value per Supplier (Top 10, 1402)
-- سؤال ۴: ده تأمین‌کننده برتر بر اساس مبلغ فروش ۱۴۰۲؛ نبود شرکت در ۱۴۰۱ برابر صفر است.
-- ========================================================================

WITH annual AS (
    SELECT
        supplier_id AS id,
        supplier_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM pharma.v_sales_dashboard
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
    ROW_NUMBER() OVER (
        ORDER BY t.value DESC, t.id
    ) AS rank_1402,
    t.id AS supplier_id,
    t.name AS supplier_name,
    CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_1401,
    t.value AS value_1402,
    t.value - (CASE WHEN b.id IS NULL THEN 0 ELSE b.value END) AS absolute_change,
    100.0 * (t.value - (CASE WHEN b.id IS NULL THEN 0 ELSE b.value END))
    / NULLIF(
        CASE WHEN b.value > 0 THEN b.value END,
        0
    ) AS growth_pct
FROM leaders AS t
LEFT JOIN annual AS b
    ON b.id = t.id
    AND b.year = 1401
ORDER BY
    t.value DESC,
    t.id;


-- ========================================================================
-- QUESTION 05 / 10 | Sales Volume per Supplier (Same Top 10 as Q4)
-- سؤال ۵: تعداد فروش دقیقاً همان شرکت‌ها و همان ترتیب سؤال ۴؛ رتبه‌بندی مجدد نمی‌شود.
-- ========================================================================

WITH annual AS (
    SELECT
        supplier_id AS id,
        supplier_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM pharma.v_sales_dashboard
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
    ROW_NUMBER() OVER (
        ORDER BY t.value DESC, t.id
    ) AS rank_1402,
    t.id AS supplier_id,
    t.name AS supplier_name,
    CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_1401,
    t.volume AS volume_1402,
    t.volume - (CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END) AS absolute_change,
    100.0 * (t.volume - (CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END))
    / NULLIF(
        CASE WHEN b.volume > 0 THEN b.volume END,
        0
    ) AS growth_pct
FROM leaders AS t
LEFT JOIN annual AS b
    ON b.id = t.id
    AND b.year = 1401
ORDER BY
    t.value DESC,
    t.id;


-- ========================================================================
-- QUESTION 06 / 10 | Sales Volume per Distributor (Top 10, 1402)
-- سؤال ۶: ده پخش‌کننده برتر بر اساس تعداد فروش ۱۴۰۲ و تغییر نسبت به ۱۴۰۱.
-- ========================================================================

WITH annual AS (
    SELECT
        distributor_id AS id,
        distributor_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM pharma.v_sales_dashboard
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
    ROW_NUMBER() OVER (
        ORDER BY t.volume DESC, t.id
    ) AS rank_1402,
    t.id AS distributor_id,
    t.name AS distributor_name,
    CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END AS volume_1401,
    t.volume AS volume_1402,
    t.volume - (CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END) AS absolute_change,
    100.0 * (t.volume - (CASE WHEN b.id IS NULL THEN 0 ELSE b.volume END))
    / NULLIF(
        CASE WHEN b.volume > 0 THEN b.volume END,
        0
    ) AS growth_pct
FROM leaders AS t
LEFT JOIN annual AS b
    ON b.id = t.id
    AND b.year = 1401
ORDER BY
    t.volume DESC,
    t.id;


-- ========================================================================
-- QUESTION 07 / 10 | Sales Value per Distributor (Same Top 10 as Q6)
-- سؤال ۷: مبلغ فروش دقیقاً همان شرکت‌ها و همان ترتیب سؤال ۶؛ رتبه‌بندی مجدد نمی‌شود.
-- ========================================================================

WITH annual AS (
    SELECT
        distributor_id AS id,
        distributor_name AS name,
        year,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM pharma.v_sales_dashboard
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
    ROW_NUMBER() OVER (
        ORDER BY t.volume DESC, t.id
    ) AS rank_1402,
    t.id AS distributor_id,
    t.name AS distributor_name,
    CASE WHEN b.id IS NULL THEN 0 ELSE b.value END AS value_1401,
    t.value AS value_1402,
    t.value - (CASE WHEN b.id IS NULL THEN 0 ELSE b.value END) AS absolute_change,
    100.0 * (t.value - (CASE WHEN b.id IS NULL THEN 0 ELSE b.value END))
    / NULLIF(
        CASE WHEN b.value > 0 THEN b.value END,
        0
    ) AS growth_pct
FROM leaders AS t
LEFT JOIN annual AS b
    ON b.id = t.id
    AND b.year = 1401
ORDER BY
    t.volume DESC,
    t.id;


-- ========================================================================
-- QUESTION 08 / 10 | Sales Value / Volume per ATC Level 1
-- سؤال ۸: مبلغ و تعداد فروش هر گروه ATC در هر سال؛ ? شامل اقلام فاقد طبقه‌بندی است.
-- ========================================================================

SELECT
    year,
    COALESCE(atc_l1, '?') AS category,
    SUM(sales_consumer_rial) AS value,
    SUM(units_sold) AS volume
FROM pharma.v_sales_dashboard
WHERE year IN (1401, 1402)
GROUP BY
    year,
    COALESCE(atc_l1, '?')
ORDER BY
    category,
    year;


-- ========================================================================
-- QUESTION 09 / 10 | Percent Stack Sales Value / Volume by ATC
-- سؤال ۹: سهم درصدی هر گروه از کل فروش همان سال؛ جمع سهم‌ها ۱۰۰٪ است. گروه ? حفظ شده است.
-- ========================================================================

WITH groups AS (
    SELECT
        year,
        COALESCE(atc_l1, '?') AS category,
        SUM(sales_consumer_rial) AS value,
        SUM(units_sold) AS volume
    FROM pharma.v_sales_dashboard
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
-- QUESTION 10 / 10 | Sales Value / Volume per OTC Status
-- سؤال ۱۰: مقایسه OTC و Rx با استفاده از پرچم موجود؛ وضعیت خالی Unknown است.
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
    FROM pharma.v_sales_dashboard
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
