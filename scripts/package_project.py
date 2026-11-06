"""Prepare distributable files and a portable repository ZIP."""
from pathlib import Path
import json,shutil,zipfile

ROOT=Path(__file__).resolve().parents[1]
from build_query_downloads import build
build()
docs=ROOT/'docs'
figures=sorted((ROOT/'evidence/figures').glob('*.svg'))
(docs/'figures').mkdir(exist_ok=True)
for file in figures:shutil.copy2(file,docs/'figures'/file.name)
gallery='''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>نمودارهای تمرین دارویی</title><link rel="stylesheet" href="style.css"><body><main style="max-width:1200px"><a href="index.html">← بازگشت به داشبورد</a><h1>نمودارهای ده سؤال تمرین</h1><p>مقایسه ۱۴۰۱ و ۱۴۰۲؛ کل بازار، بدون فیلتر. فایل‌های SVG شامل فونت فارسی‌اند.</p><div class="grid">'''
for file in figures:
    gallery+=f'<article class="panel"><a href="figures/{file.name}" download><img src="figures/{file.name}" alt="{file.stem}" style="width:100%;height:auto"><p style="padding:10px 20px">↓ {file.stem}</p></a></article>'
gallery+='</div></main></body></html>'
(docs/'gallery.html').write_text(gallery,encoding='utf-8')
shutil.copy2(ROOT/'README.md',docs/'downloads/methodology.md')
shutil.copy2(ROOT/'sql/analytical_queries.sql',docs/'downloads/analytical_queries.sql')
shutil.copy2(ROOT/'sql/postgresql_queries.sql',docs/'downloads/postgresql_queries.sql')
with zipfile.ZipFile(docs/'downloads/figures.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for file in figures:z.write(file,file.name)
archive=ROOT.parent/'pharma_dashboard_github.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in ROOT.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts and p.name!='dashboard.sqlite':
            z.write(p,Path(ROOT.name)/p.relative_to(ROOT))
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'figures':len(figures)}))
