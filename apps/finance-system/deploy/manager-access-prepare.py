"""Metadata + local pre-edit snapshots for explicit manager rollout1546858367635685396."""
import pathlib,json,re,hashlib,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
STATE=ROOT/'private/manager-access-1546858367635685396';STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
FILES=['manager-view.mjs','finance-ops.mjs','public/operations.js','public/navigation.js']
BEFORE=STATE/'before';BEFORE.mkdir(exist_ok=True)
for f in FILES:
 p=BEFORE/f;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():shutil.copy2(ROOT/f,p)
s=json.loads((ROOT/'private/source.json').read_text());out={'metadata_only':True,'authority':'1546858367635685396','managers':{}}
expected={'joe':5,'kelly':6,'isliago':8,'george':9,'nicolas':8}
for key,name in [('joe','Joe'),('kelly','Kelly'),('isliago','Isliago'),('george','Ícaro'),('nicolas','Nicolas')]:
 cells=[x for x in s['cells'] if x['book']==key and x['sheet']=='Agosto 2026'];blocks=[]
 for c in cells:
  val=c.get('expected')
  if not re.fullmatch(r'B\d+',c['cell']) or int(c['cell'][1:])<=15 or not isinstance(val,str) or not re.search(r'\n(?:CAD|GBP|GROSS)(?:\n|$)',val):continue
  row=int(c['cell'][1:]);cols=[]
  for x in cells:
   if int(re.search(r'\d+$',x['cell'])[0])!=row or x['cell'].startswith('A') and re.fullmatch(r'A\d+',x['cell']):continue
   v=x.get('expected')
   if isinstance(v,str) and v.strip():cols.append({'col':re.sub(r'\d+','',x['cell']),'label':v.replace('\n',' · ')})
  def colnum(x):
   n=0
   for a in x['col']:n=n*26+ord(a)-64
   return n
  cols.sort(key=colnum)
  if key=='george' and row==207:
   country_metrics=['CAD','GROSS','Invalido','NET','Imposto','Gastos','LUCRO LIQUIDO','ROI · GROSS','ROI · NET']
   total_metrics=['Receita NET','Imposto','Despesas','Invalido','Gastos','LUCRO LIQUIDO','ROI · GROSS','ROI · NET']
   assert len(cols)==35
   for i,c in enumerate(cols):
    c['source_label']=c['label'];c['label']=(country_metrics[i%9]+' · '+['US','BR','GB'][i//9]) if i<27 else total_metrics[i-27]+' · TOTAL'
  blocks.append({'row':row,'label':val.split('\n')[0], 'columns':cols})
 assert len(blocks)==expected[key],(key,len(blocks))
 out['managers']['icaro' if key=='george' else key]={'book':key,'display_name':name,'blocks':blocks}
# Preserve the already validated Nicolas metadata literally.
old=json.loads((ROOT/'manager-layout.json').read_text());assert out['managers']['nicolas']['blocks']==old['blocks']
p=ROOT/'manager-layouts.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':True,'blocks':{k:len(v['blocks']) for k,v in out['managers'].items()},'metadata_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
