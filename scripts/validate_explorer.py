import sqlite3,json,subprocess,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
q=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./docs/queries.js').QUERY_DEFS))"],cwd=root))
c=sqlite3.connect(root/'docs/data/dashboard.sqlite');c.row_factory=sqlite3.Row
params={'base':1401,'target':1402,'supplier':0,'distributor':0,'atc':'','otc':-1,'origin':'','search':'','pattern':'%%'}
js="const fs=require('fs'),vm=require('vm');const s=fs.readFileSync('docs/app.js','utf8');const ctx={};vm.createContext(ctx);vm.runInContext(s.slice(s.indexOf('function explorerAggregate'),s.indexOf('function mountExplorer')),ctx);const x=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(ctx.explorerAggregate(x.rows,x.period,x.metric,1401,1402)));"
checks=0
for role in ['supplier','distributor']:
 rows=[dict(r) for r in c.execute(q[role+'_explorer'],params)]
 for period,years in [('base','1401'),('target','1402'),('both','1401,1402')]:
  for metric,col in [('value','sales_consumer_rial'),('volume','units_sold')]:
   out=json.loads(subprocess.check_output(['node','-e',js],cwd=root,input=json.dumps({'rows':rows,'period':period,'metric':metric}).encode()))
   expected=c.execute(f'SELECT {role}_id id,SUM({col}) amount FROM fact_sales WHERE year IN ({years}) AND {role}_id IS NOT NULL GROUP BY {role}_id HAVING SUM({col})>0 ORDER BY amount DESC,id LIMIT 10').fetchall()
   assert [r['id'] for r in out['leaders']]==[r['id'] for r in expected]
   for a,b in zip(out['leaders'],expected):assert math.isclose(a['amount'],b['amount'],rel_tol=1e-11)
   checks+=1
(root/'evidence/explorer-validation.json').write_text(json.dumps({'status':'passed','independent_rankings':checks}),encoding='utf-8')
print(f'Passed {checks} independent explorer rankings, including combined-year totals.')
