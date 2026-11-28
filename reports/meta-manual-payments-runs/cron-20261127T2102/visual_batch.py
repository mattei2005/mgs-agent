import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
B=Path(__file__).parent;H=Path(json.loads((B/'h_prepare.log').read_text())['run_dir']);T=json.loads((H/'targets.json').read_text())
if sys.argv[1]=='board':
 n=int(sys.argv[2]);ims=[]
 for t in T[(n-1)*6:n*6]:
  im=Image.open(H/(t['account_id']+'.png'));w,ht=im.size
  panel=Image.new('RGB',(2390,365),'white');panel.paste(im.crop((120,35,min(w,2510),90)),(0,25));panel.paste(im.crop((390,545,min(w,2510),min(ht,825))),(0,85));ImageDraw.Draw(panel).text((0,0),'SOURCE '+t['account_id']+'.png',fill='black');ims.append(panel)
 out=Image.new('RGB',(2390,sum(i.height for i in ims)),'white');y=0
 for im in ims:out.paste(im,(0,y));y+=im.height
 out.save(B/('h-visual-batch'+str(n)+'.png'));print(str(B/('h-visual-batch'+str(n)+'.png')))
elif sys.argv[1]=='record':
 p=H/'visual-verification.json';d=json.loads(p.read_text())if p.exists()else{'verified_account_ids':[],'accounts_list_checks':{}}
 for pair in sys.argv[2:]:
  aid,amount=pair.split('=');r=json.loads((H/(aid+'-receipt.json')).read_text());assert r['amount']==amount;assert r['business_id']=='155263197283282';assert any(t['account_id']==aid and t['name']==r['name']for t in T)
  assert aid not in d['verified_account_ids'];d['verified_account_ids'].append(aid);d['accounts_list_checks'][aid]={'valid_billing_list':True,'business_id':'155263197283282','row_account_id':aid,'name':r['name'],'balance_usd':amount,'balance_label':'Outstanding balance','authority_message_id':'1570815017794674749'}
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600);print('verified',len(d['verified_account_ids']))
