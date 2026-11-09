import json,sys,os
from pathlib import Path
from decimal import Decimal
B=Path(__file__).parent;ph=json.loads((B/'phases.json').read_text());P=Path(ph['publish_pay_now']['run_dir']);out=P/'visual-verification.json'
d=json.loads(out.read_text())if out.exists()else{'verified_account_ids':[],'accounts_list_checks':{}}
rows=json.loads(sys.argv[1])
for aid,name,amount in rows:
 r=json.loads((P/(aid+'-receipt.json')).read_text());assert r['account_id']==aid and r['name']==name and Decimal(r['amount'])==Decimal(amount)
 d['accounts_list_checks'][aid]={'valid_billing_list':True,'business_id':'155263197283282','row_account_id':aid,'name':name,'balance_usd':amount}
d['verified_account_ids']=sorted(d['accounts_list_checks']);out.write_text(json.dumps(d,ensure_ascii=False,indent=2));out.chmod(0o600);print('visually_verified',len(d['verified_account_ids']))
