import {PGlite} from '@electric-sql/pglite';import fs from 'node:fs/promises';import {createHash,randomUUID} from 'node:crypto';import path from 'node:path';import {authSchema} from '../auth.mjs';
const root=path.resolve(new URL('..',import.meta.url).pathname);const source=process.argv[2];if(!source)throw Error('source required');
const db=await PGlite.create(source);await db.exec("SET timezone='UTC'");
const tables=['imports','source_cells','scenarios','entity_versions','audit_events','acceptance_runs'];
const order={imports:'id',source_cells:'import_id,id',scenarios:'id',entity_versions:'scenario_id,entity_id,version',audit_events:'id',acceptance_runs:'id'};
export const stable=v=>v&&typeof v==='object'?Array.isArray(v)?v.map(stable):Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])])):v;
const manifest={};let sql='BEGIN;\n'+await fs.readFile(path.join(root,'schema.sql'),'utf8')+'\n'+authSchema+'\n';
for(const table of tables){const rows=(await db.query(`SELECT to_jsonb(t) AS row FROM ${table} t ORDER BY ${order[table]}`)).rows.map(x=>x.row);manifest[table]={count:rows.length,sha256:createHash('sha256').update(JSON.stringify(stable(rows))).digest('hex')};for(let i=0;i<rows.length;i+=1000){const text=JSON.stringify(rows.slice(i,i+1000));let tag;do{tag='$mgs'+randomUUID().replaceAll('-','')+'$'}while(text.includes(tag));sql+=`INSERT INTO ${table} OVERRIDING SYSTEM VALUE SELECT * FROM jsonb_populate_recordset(NULL::${table},${tag}${text}${tag}::jsonb);\n`;}}
sql+="SELECT setval(pg_get_serial_sequence('audit_events','id'),COALESCE((SELECT max(id) FROM audit_events),1),true);\nCOMMIT;\n";
await fs.writeFile(path.join(root,'private/migration.sql'),sql,{mode:0o600});await fs.writeFile(path.join(root,'private/migration-manifest.json'),JSON.stringify({tables:manifest,order},null,2),{mode:0o600});await db.close();console.log(JSON.stringify({exported:manifest,sql_sha256:createHash('sha256').update(sql).digest('hex')}));
