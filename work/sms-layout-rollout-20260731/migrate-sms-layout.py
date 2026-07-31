#!/usr/bin/env python3
import argparse,copy,json,os,tempfile
from pathlib import Path
from urllib.parse import urlparse

GATE={
 'enabled':True,
 'questions':[{'text':'🚗 Qual a faixa de preço do carro que você deseja?','answers':[
  {'label':'R$ 30.000 a R$ 45.000','value':'30000-45000'},
  {'label':'R$ 45.000 a R$ 60.000','value':'45000-60000'},
  {'label':'R$ 60.000 a R$ 80.000','value':'60000-80000'},
  {'label':'Acima de R$ 80.000','value':'80000+'}], 'enabled':True}],
 'loading_text':'','loading_ms':0,'final_icon':'🚗','final_title':'Oferta encontrada!',
 'final_subtitle':'Um especialista foi identificado para te atender agora.',
 'cta_label':'TRANSFERIR PARA ESPECIALISTA →','footer_note':'✅ Análise gratuita e sem compromisso','skip_loading':True,
}
LAYOUT={
 'sms_name_label':'Nome','sms_phone_label':'Telefone','sms_submit_label':'VER PARCELAS',
 'sms_optional':True,'sms_compact_gate':True,'sms_form_intro':'Preencha seus dados e veja as parcelas:',
 'sms_gate_image':'default','sms_gate_image_alt':'Carro disponível para financiamento',
 'geo_enabled':True,'geo_prefix_text':'Analisando ofertas de veículos em',
 'geo_fallback_text':'Analisando ofertas disponíveis na sua região',
 'sms_consent_enabled':True,'sms_consent_default':True,'sms_consent_label':'Aceito receber ofertas por SMS.',
 'sms_skip_label':'Pular, quero ver as ofertas',
}
LEGAL={
 'eggbev.com':[('Privacidade','/privacy-policy/'),('Termos','/terms-of-service/'),('Sobre','/about-us/')],
 'newsoun.com':[('Privacidade','/privacy-policy/'),('Termos','/terms-of-service/'),('Sobre','/about-us/')],
 'finance.topfeed.fun':[('Privacidade','/privacy-policy/'),('Termos','/terms-of-use/'),('Sobre','/about-us/')],
 'wantabrand.com':[('Privacidade','/politica-de-privacidad/'),('Termos','/terms-of-service/'),('Sobre','/sobre-nosotros/')],
 'zytiva.com':[('Privacidade','/privacy-policy/'),('Termos','/terms-of-service/'),('Sobre','/about-us/')],
 'openzed.com':[('Privacidade','/privacy-policy/'),('Termos','/terms-of-use/'),('Sobre','/about/')],
 'cliquet.com':[('Privacidade','/privacy-policy/'),('Termos','/terms/'),('Sobre','/about/')],
}
ALLOWED={'gate','legal_links',*LAYOUT.keys()}

def diff(a,b,p=''):
 out=[]
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)): out+=diff(a.get(k),b.get(k),f'{p}.{k}'.strip('.'))
 elif isinstance(a,list) and isinstance(b,list):
  if len(a)!=len(b): out.append(p+'.length')
  for i,(x,y) in enumerate(zip(a,b)): out+=diff(x,y,f'{p}.{i}'.strip('.'))
 elif a!=b: out.append(p)
 return out

def validate(c,domain):
 if c.get('id')!='CAR-BR-01-SMS' or c.get('route')!='/chat-sms/car/br1' or c.get('mode')!='cards' or not c.get('sms_enabled'):
  raise ValueError(f'{domain}: unexpected SMS config identity/route/mode/state')
 if not c.get('sms_manager_code'): raise ValueError(f'{domain}: SMS manager missing')
 offers=c.get('offers')
 if not isinstance(offers,list) or len(offers)!=3: raise ValueError(f'{domain}: expected exactly three offers')
 for offer in offers:
  target=offer.get('target') or offer.get('url') or ''
  if (urlparse(target).hostname or '').lower()!=domain: raise ValueError(f'{domain}: missing/cross-domain offer target')
 provider=str(c.get('ad_provider') or '').lower()
 if domain=='wantabrand.com':
  if provider!='m2' or c.get('ad_company')!='monetizemore': raise ValueError('wantabrand.com: M2 provider contract missing')
 elif provider in {'m2','actview','zuout-actview'}:
  raise ValueError(f'{domain}: unexpected exclusive provider {provider}')

def migrate(c,domain):
 domain=domain.lower().strip()
 if domain not in LEGAL: raise ValueError(f'{domain}: no verified legal map')
 validate(c,domain); before=copy.deepcopy(c); out=copy.deepcopy(c)
 out['gate']=copy.deepcopy(GATE)
 for k,v in LAYOUT.items(): out[k]=copy.deepcopy(v)
 out['legal_links']=[{'label':label,'url':f'https://{domain}{path}'} for label,path in LEGAL[domain]]
 validate(out,domain)
 changed=diff(before,out)
 if any(path.split('.',1)[0] not in ALLOWED for path in changed):
  raise ValueError(f'{domain}: unexpected changed paths {changed}')
 return out,changed

def atomic_write(path,obj):
 path=Path(path); fd,tmp=tempfile.mkstemp(prefix='.zeus-sms-layout-',suffix='.json',dir=path.parent,text=True)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:
   json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  json.load(open(tmp,encoding='utf-8'));os.replace(tmp,path)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('domain');ap.add_argument('--output');args=ap.parse_args()
 src=Path(args.input);c=json.load(open(src,encoding='utf-8'));out,changed=migrate(c,args.domain)
 dst=Path(args.output) if args.output else src;atomic_write(dst,out)
 print(json.dumps({'domain':args.domain,'output':str(dst),'changed_paths':changed,'manager':out['sms_manager_code'],'provider':out.get('ad_provider') or 'jbf-default'},ensure_ascii=False,separators=(',',':')))
if __name__=='__main__': main()
