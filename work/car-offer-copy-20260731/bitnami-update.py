#!/usr/bin/env python3
import copy,html,json,os,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,urlparse
import requests

ROOT=Path('/root/mgs-agent')
BACKUP_ROOT=ROOT/'backups'/'car-offer-copy'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
SITES=[
 {'domain':'openzed.com','item':'i63tdlbsjyh5tt2w4kawfx4zmq'},
 {'domain':'cliquet.com','item':'6agocinssvqkv3f5ftfeujiemi'},
]
DESIRED=['🚗 Financiar sem entrada','💰 Ver ofertas disponíveis','🚘 Financiamento com parcela baixa']


def op_field(item,label):
 return subprocess.check_output(['op','item','get',item,'--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields',f'label={label}','--reveal'],text=True).strip()


def login(site):
 domain=site['domain']; username=op_field(site['item'],'username'); password=op_field(site['item'],'password')
 try: login_url=op_field(site['item'],'login_ur')
 except subprocess.CalledProcessError: login_url=f'https://{domain}/rodloguda/'
 if not login_url.startswith('http'): login_url=f'https://{domain}/rodloguda/'
 s=requests.Session(); s.headers['User-Agent']='Mozilla/5.0 MGS-Zeus-Offer-Copy'
 first=s.get(login_url,timeout=30); first.raise_for_status()
 m=re.search(r'<form[^>]+id=["\']loginform["\'][^>]+action=["\']([^"\']+)',first.text,re.I)
 action=html.unescape(m.group(1)) if m else first.url
 r=s.post(action,data={'log':username,'pwd':password,'wp-submit':'Log In','redirect_to':f'https://{domain}/wp-admin/','testcookie':'1'},headers={'Referer':first.url},timeout=30,allow_redirects=True); r.raise_for_status()
 probe=s.get(f'https://{domain}/wp-admin/profile.php',timeout=30)
 if probe.status_code!=200 or 'loginform' in probe.text or 'user_login' not in probe.text: raise RuntimeError(f'{domain}: authenticated probe failed')
 return s


def raw_config(s,domain,config_id):
 u=f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels&funnel={quote(config_id)}'
 r=s.get(u,timeout=35); r.raise_for_status()
 m=re.search(r'<textarea[^>]+name=["\']raw_json["\'][^>]*>(.*?)</textarea>',r.text,re.S|re.I)
 if not m: raise RuntimeError(f'{domain}: config {config_id} missing')
 return json.loads(html.unescape(m.group(1)))


def save_raw(s,domain,config):
 page=s.get(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels',timeout=35); page.raise_for_status()
 n=re.search(r'name=["\']mgs_cf_nonce["\'][^>]+value=["\']([^"\']+)',page.text,re.I)
 if not n: raise RuntimeError(f'{domain}: nonce missing')
 r=s.post(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels',data={'mgs_cf_nonce':html.unescape(n.group(1)),'mgs_cf_action':'save_raw','raw_json':json.dumps(config,ensure_ascii=False,indent=2)+'\n'},headers={'Referer':page.url},timeout=45); r.raise_for_status()
 if 'JSON salvo com sucesso' not in r.text: raise RuntimeError(f'{domain}: save not confirmed for {config["id"]}')
 if raw_config(s,domain,config['id'])!=config: raise RuntimeError(f'{domain}: exact readback failed for {config["id"]}')


def diff(a,b,p=''):
 out=[]
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)): out+=diff(a.get(k),b.get(k),f'{p}.{k}'.strip('.'))
 elif isinstance(a,list) and isinstance(b,list):
  if len(a)!=len(b): out.append(p+'.length')
  for i,(x,y) in enumerate(zip(a,b)): out+=diff(x,y,f'{p}.{i}'.strip('.'))
 elif a!=b: out.append(p)
 return out


def desired(c,domain,config_id,route):
 if c.get('id')!=config_id or c.get('route')!=route or c.get('mode')!='cards': raise RuntimeError(f'{domain}: unexpected identity/route/mode for {config_id}')
 if len(c.get('offers',[]))!=3: raise RuntimeError(f'{domain}: expected 3 offers in {config_id}')
 if any((urlparse(x.get('target') or x.get('url') or '').hostname or '').lower()!=domain for x in c['offers']): raise RuntimeError(f'{domain}: target drift in {config_id}')
 out=copy.deepcopy(c)
 for offer,name in zip(out['offers'],DESIRED): offer['name']=name
 out['offers'][2]['subtitle']='Consulte se essa condição está disponível para você,'
 allowed={f'offers.{i}.name' for i in range(3)}|{'offers.2.subtitle'}
 changed=set(diff(c,out))
 if not changed.issubset(allowed): raise RuntimeError(f'{domain}: unexpected changes {sorted(changed)}')
 return out


def main():
 selected={x.strip() for x in os.environ.get('MGS_TARGET_DOMAINS','').split(',') if x.strip()}
 sites=[x for x in SITES if not selected or x['domain'] in selected]
 if not sites: raise RuntimeError('no Bitnami target selected')
 BACKUP_ROOT.mkdir(parents=True,exist_ok=True); os.chmod(BACKUP_ROOT,0o700)
 results=[]
 for site in sites:
  domain=site['domain']; print(f'BEGIN|{domain}',flush=True); s=login(site)
  originals={
   'CAR-BR-01':raw_config(s,domain,'CAR-BR-01'),
   'CAR-BR-01-SMS':raw_config(s,domain,'CAR-BR-01-SMS'),
  }
  site_backup=BACKUP_ROOT/domain; site_backup.mkdir(parents=True,exist_ok=True); os.chmod(site_backup,0o700)
  for cid,c in originals.items():
   p=site_backup/(cid.lower()+'.json'); p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n'); os.chmod(p,0o600)
  after={
   'CAR-BR-01':desired(originals['CAR-BR-01'],domain,'CAR-BR-01','/chat/car/br1'),
   'CAR-BR-01-SMS':desired(originals['CAR-BR-01-SMS'],domain,'CAR-BR-01-SMS','/chat-sms/car/br1'),
  }
  changed=[]
  try:
   for cid in ('CAR-BR-01','CAR-BR-01-SMS'):
    save_raw(s,domain,after[cid]); changed.append(cid)
   for cid in after:
    rb=raw_config(s,domain,cid)
    if [x.get('name') for x in rb['offers']]!=DESIRED or rb['offers'][2].get('subtitle')!='Consulte se essa condição está disponível para você,': raise RuntimeError(f'{domain}: final copy readback failed for {cid}')
   print(f'COMPLETE|{domain}|configs=2|backup={site_backup}',flush=True)
   results.append({'domain':domain,'ok':True,'backup':str(site_backup)})
  except Exception:
   for cid in reversed(changed):
    try: save_raw(s,domain,originals[cid])
    except Exception as rollback_error: print(f'ROLLBACK_FAILED|{domain}|{cid}|{type(rollback_error).__name__}',flush=True)
   raise
 manifest={'backup_root':str(BACKUP_ROOT),'sites':results}
 (BACKUP_ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'complete':True,'backup_root':str(BACKUP_ROOT),'sites':[x['domain'] for x in results]},ensure_ascii=False),flush=True)

if __name__=='__main__': main()
