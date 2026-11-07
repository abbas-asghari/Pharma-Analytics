"""Ten independently executable PostgreSQL answers, matching the assignment."""
from pathlib import Path
import re
from build_query_downloads import company, section
ROOT=Path(__file__).resolve().parents[1]

def query_body(section_text):
    return re.search(r'\n\n((?:WITH|SELECT)[\s\S]*);\s*$',section_text).group(1)

def build_postgresql(source_sections):
    answers=[]
    answers.append(section('QUESTION 01 / 10 | Sales Volume / Sales Value per Year',
        'سؤال ۱: مقایسه مجموع تعداد و مبلغ فروش سال‌های ۱۴۰۱ و ۱۴۰۲؛ مبلغ به ریال.', '''SELECT
    year,
    SUM(units_sold) AS sales_volume,
    SUM(sales_consumer_rial) AS sales_value_rial
FROM pharma.fact_sales
WHERE year IN (1401, 1402)
GROUP BY
    year
ORDER BY
    year'''))
    for q,col,metric,fa in [(2,'sales_consumer_rial','sales_value','مبلغ'),(3,'units_sold','sales_volume','تعداد')]:
        answers.append(section(f'QUESTION {q:02d} / 10 | '+('Sales Value' if q==2 else 'Sales Volume')+' Growth Rate (1401 -> 1402)',
            f'سؤال {q}: نرخ رشد {fa} فروش؛ خروجی درصد است. پایه صفر یا منفی: NULL.', f'''WITH annual AS (
    SELECT
        year,
        SUM({col}) AS amount
    FROM pharma.fact_sales
    WHERE year IN (1401, 1402)
    GROUP BY
        year
)
SELECT
    base.amount AS {metric}_1401,
    target.amount AS {metric}_1402,
    target.amount - base.amount AS absolute_change,
    100.0 * (target.amount - base.amount)
    / NULLIF(
        CASE WHEN base.amount > 0 THEN base.amount END,
        0
    ) AS growth_pct
FROM annual AS base
JOIN annual AS target
    ON base.year = 1401
    AND target.year = 1402'''))
    for q,role,rank,metric,title,note in [
        (4,'supplier','value','value','Sales Value per Supplier (Top 10, 1402)','سؤال ۴: ده تأمین‌کننده برتر بر اساس مبلغ فروش ۱۴۰۲؛ نبود شرکت در ۱۴۰۱ برابر صفر است.'),
        (5,'supplier','value','volume','Sales Volume per Supplier (Same Top 10 as Q4)','سؤال ۵: تعداد فروش دقیقاً همان شرکت‌ها و همان ترتیب سؤال ۴؛ رتبه‌بندی مجدد نمی‌شود.'),
        (6,'distributor','volume','volume','Sales Volume per Distributor (Top 10, 1402)','سؤال ۶: ده پخش‌کننده برتر بر اساس تعداد فروش ۱۴۰۲ و تغییر نسبت به ۱۴۰۱.'),
        (7,'distributor','volume','value','Sales Value per Distributor (Same Top 10 as Q6)','سؤال ۷: مبلغ فروش دقیقاً همان شرکت‌ها و همان ترتیب سؤال ۶؛ رتبه‌بندی مجدد نمی‌شود.')]:
        prefix=company(role,rank).split('\nSELECT\n    t.id,')[0]
        baseline=f'CASE WHEN b.id IS NULL THEN 0 ELSE b.{metric} END'
        suffix=f'''\nSELECT
    ROW_NUMBER() OVER (
        ORDER BY t.{rank} DESC, t.id
    ) AS rank_1402,
    t.id AS {role}_id,
    t.name AS {role}_name,
    {baseline} AS {metric}_1401,
    t.{metric} AS {metric}_1402,
    t.{metric} - ({baseline}) AS absolute_change,
    100.0 * (t.{metric} - ({baseline}))
    / NULLIF(
        CASE WHEN b.{metric} > 0 THEN b.{metric} END,
        0
    ) AS growth_pct
FROM leaders AS t
LEFT JOIN annual AS b
    ON b.id = t.id
    AND b.year = 1401
ORDER BY
    t.{rank} DESC,
    t.id'''
        answers.append(section(f'QUESTION {q:02d} / 10 | {title}',note,prefix+suffix))
    for q,index,title,note in [
        (8,4,'Sales Value / Volume per ATC Level 1','سؤال ۸: مبلغ و تعداد فروش هر گروه ATC در هر سال؛ ? شامل اقلام فاقد طبقه‌بندی است.'),
        (9,5,'Percent Stack Sales Value / Volume by ATC','سؤال ۹: سهم درصدی هر گروه از کل فروش همان سال؛ جمع سهم‌ها ۱۰۰٪ است. گروه ? حفظ شده است.'),
        (10,6,'Sales Value / Volume per OTC Status','سؤال ۱۰: مقایسه OTC و Rx با استفاده از پرچم موجود؛ وضعیت خالی Unknown است.')]:
        answers.append(section(f'QUESTION {q:02d} / 10 | {title}',note,query_body(source_sections[index])))
    text='''-- PHARMA ANALYTICS | PostgreSQL | Questions 01-10
-- ابتدا فایل data/pharma_1401_1404.sql را در دیتابیس وارد کنید.
-- هر بخش را مستقل در Query Tool اجرا کنید؛ نام schema در کوئری‌ها مشخص است.
-- دامنه: سال‌های ۱۴۰۱ و ۱۴۰۲، همه شرکت‌ها و محصولات.
-- value: ریال | volume: واحد گزارش‌شده | growth_pct و share_pct: درصد
-- سؤال ۵ ترتیب سؤال ۴ و سؤال ۷ ترتیب سؤال ۶ را حفظ می‌کند.
-- سؤال‌های ۸ و ۹ گروه فاقد ATC را برای تطبیق با کل بازار حفظ می‌کنند.
-- نمودار سایت گروه فاقد ATC را نمایش نمی‌دهد و درصدها را بر اقلام دارای ATC محاسبه می‌کند.

'''+ '\n\n'.join(answers)
    text=text.replace('FROM v_sales_dashboard','FROM pharma.v_sales_dashboard').replace('is_otc = 1','is_otc = TRUE').replace('is_otc = 0','is_otc = FALSE')
    (ROOT/'sql/postgresql_queries.sql').write_text(text,encoding='utf-8')
