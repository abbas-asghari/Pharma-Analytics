importScripts('vendor/sql-wasm.js','queries.js');
let db;
function query(sql, params={}) {
 const stmt=db.prepare(sql);const rows=[];
 try {stmt.bind(params);while(stmt.step())rows.push(stmt.getAsObject());}
 finally {stmt.free();}return rows;
}
self.onmessage=async({data})=>{
 try {
  if(data.type==='init') {
   postMessage({type:'status',message:'دریافت دیتابیس فروش…'});
   const [SQL,response]=await Promise.all([
    initSqlJs({locateFile:f=>'vendor/'+f}),fetch('data/dashboard.sqlite.gz')]);
   if(!response.ok)throw Error('دریافت دیتابیس ناموفق بود: '+response.status);
   if(!self.DecompressionStream)throw Error('لطفاً از نسخه جدید Chrome، Edge، Firefox یا Safari استفاده کنید.');
   const bytes=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   postMessage({type:'status',message:'آماده‌سازی موتور تحلیل…'});
   db=new SQL.Database(new Uint8Array(bytes));
   const options={
    years:query('SELECT DISTINCT year FROM fact_sales ORDER BY year'),
    suppliers:query('SELECT DISTINCT supplier_id AS id,supplier_name AS name FROM v_sales_dashboard WHERE supplier_id IS NOT NULL ORDER BY name'),
    distributors:query('SELECT DISTINCT distributor_id AS id,distributor_name AS name FROM v_sales_dashboard WHERE distributor_id IS NOT NULL ORDER BY name'),
    atc:query("SELECT DISTINCT COALESCE(atc_l1,'?') AS code FROM dim_product ORDER BY code"),
    origins:query('SELECT DISTINCT origin AS name FROM dim_product WHERE origin IS NOT NULL ORDER BY origin')
   };
   postMessage({type:'ready',options});
  } else if(data.type==='query') {
   if(!db)throw Error('دیتابیس هنوز آماده نیست.');
   const results={};
   for(const [key,sql] of Object.entries(QUERY_DEFS))results[key]=query(sql,data.params);
   postMessage({type:'results',id:data.id,results});
  }
 }catch(e){postMessage({type:'error',id:data.id,message:String(e.message||e)});}
};
