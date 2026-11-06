import json,sys
from pathlib import Path
from decimal import Decimal
B=Path(__file__).parent;P=Path(json.loads((B/'phases.json').read_text())['publish_pay_now']['run_dir']);f=P/'visual-verification.json';d=json.loads(f.read_text())if f.exists()else{'verified_account_ids':[],'accounts_list_checks':{}}
rows=json.loads(sys.argv[1])
for aid,name,amount in rows:
 r=json.loads((P/(aid+'-receipt.json')).read_text());assert r['name']==name and Decimal(r['amount'])==Decimal(amount) and r['business_id']=='155263197283282'
 d['accounts_list_checks'][aid]={'valid_billing_list':True,'business_id':'155263197283282','row_account_id':aid,'name':name,'balance_usd':amount};d['verified_account_ids']=sorted(d['accounts_list_checks'])
f.write_text(json.dumps(d,ensure_ascii=False,indent=2));f.chmod(0o600);print('VERIFIED',len(d['verified_account_ids']))
