"""Remote filesystem queue transport only; runs as existing mgsfinance user via SSH."""
import pathlib,sys,json,time,re,datetime,os
ROOT=pathlib.Path(__file__).resolve().parents[1];DIR=ROOT/'private/meta-account-lookups'
UUID=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
def pending():
 if not DIR.exists():return []
 rows=[]
 for f in sorted(DIR.glob('*.json')):
  if not UUID.fullmatch(f.stem):continue
  d=json.loads(f.read_text())
  if d.get('status')=='pending':
   assert d.get('request_id')==f.stem and re.fullmatch(r'\d{5,30}',d.get('account_id',''))
   rows.append({**{k:d[k] for k in ['request_id','account_id','requested_at']},'platform':d.get('platform','meta')})
 return rows[:16]
if sys.argv[1]=='wait':
 deadline=time.monotonic()+45
 while True:
  rows=pending()
  if rows or time.monotonic()>=deadline:print(json.dumps(rows));break
  time.sleep(1)
elif sys.argv[1]=='complete':
 values=json.load(sys.stdin);assert isinstance(values,list) and len(values)<=16;done=[]
 for v in values:
  id=v['request_id'];assert UUID.fullmatch(id);p=DIR/(id+'.json');old=json.loads(p.read_text());assert old['status']=='pending' and old['account_id']==v['account_id']
  allowed={k:v[k] for k in ['status','name','currency','timezone','business_id','verified_at','error','accounts'] if k in v};assert allowed['status'] in ['ready','error']
  if allowed['status']=='ready':
   if old.get('platform')=='google':
    assert old['account_id']=='8137016595' and allowed.get('business_id')=='8137016595' and isinstance(allowed.get('accounts'),list)
    assert len({a['account_id'] for a in allowed['accounts']})==len(allowed['accounts'])
    for a in allowed['accounts']:assert re.fullmatch(r'\d{10}',a['account_id']) and a.get('platform')=='google' and a.get('business_id')=='8137016595' and a.get('currency') and a.get('timezone')
   else:assert allowed.get('business_id')=='155263197283282' and allowed.get('name') and allowed.get('currency') and allowed.get('timezone')
  out={**old,**allowed};temp=p.with_suffix('.pending');temp.write_text(json.dumps(out,ensure_ascii=False));temp.chmod(0o600);os.replace(temp,p);assert json.loads(p.read_text())==out;done.append(id)
 print(json.dumps({'completed':done,'readback':True}))
else:raise ValueError('Unsupported queue action')
