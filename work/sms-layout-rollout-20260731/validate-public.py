#!/usr/bin/env python3
import concurrent.futures,json,re,time
from urllib.parse import urljoin,urlparse
import requests

SITES={
 'zuout.com':'actview','zytiva.com':'jbf','openzed.com':'jbf','finance.topfeed.fun':'jbf',
 'newsoun.com':'jbf','wantabrand.com':'m2','cliquet.com':'jbf','eggbev.com':'jbf',
}
RANGES=['R$ 30.000 a R$ 45.000','R$ 45.000 a R$ 60.000','R$ 60.000 a R$ 80.000','Acima de R$ 80.000']
OFFERS=['Financiar sem entrada','Ver ofertas disponíveis','Financiamento com parcela baixa']
HEAD={'User-Agent':'MGS-Zeus-SMS-Layout-Validation','Cache-Control':'no-cache'}

def get(url):
 r=requests.get(url,timeout=40,headers=HEAD);return r

def extract_legal(html):
 m=re.search(r'<nav[^>]+aria-label="Links legais"[^>]*>(.*?)</nav>',html,re.S|re.I)
 return re.findall(r'href="([^"]+)"',m.group(1),re.I) if m else []

def validate_route(site,kind):
 route='/chat-sms/car/br1/' if kind=='sms' else '/chat/car/br1/'
 r=get('https://'+site+route+'?cb=matrix-'+str(int(time.time())))
 t=r.text;provider=SITES[site];c={
  'http':r.status_code==200,'html':'text/html' in r.headers.get('content-type',''),
  'code_045':'triggerTrustedRewarded' in t and '["av-rewarded", "pg-rewarded"]' in t,
  'offers':all(x in t for x in OFFERS),'no_loop5':'for (let i = 0; i < 5; i++)' not in t,
 }
 if provider=='jbf':
  ad='topfeed' if site=='finance.topfeed.fun' else site.split('.')[0]
  wrapper=f'https://assets.jbfdigital.com.br/assets/digital-trust/{ad}/digital-trust_{ad}.builder.js'
  c|={'provider':t.count(wrapper)==1 and all(x in t for x in ['requestRewardAds','showRewardedAds']),
      'top':all(x in t for x in ['onInfinitePostLoaded','adBanner.dataset.position = "top"']),
      'foreign':'pg.wantabrand.js' not in t and 'scr.actview.net' not in t}
 elif provider=='m2':
  c|={'provider':t.count('https://c.pubguru.net/pg.wantabrand.js')==1 and 'pg-rewarded' in t,
      'top':all(x in t for x in ['wantabrand_mob_top','wantabrand_desk_top','defineObserveredNode']),
      'foreign':all(x not in t.lower() for x in ['jbftag','showrewardedads','requestrewardads','assets.jbfdigital']) and 'scr.actview.net' not in t}
 else:
  c|={'provider':t.count('https://scr.actview.net/zuout.js')==1 and all(x in t for x in ['av-rewarded','zout_rewarded']),
      'top':all(x in t for x in ['zout_top_wrapper','zout_top']),
      'foreign':'pg.wantabrand.js' not in t and 'jbftag' not in t.lower()}
 extras={}
 if kind=='sms':
  links=extract_legal(t)
  img_tag=re.search(r'<img[^>]+alt="Carro disponível para financiamento"[^>]*>',t,re.I)
  img=re.search(r'src="([^"]+)"',img_tag.group(0),re.I) if img_tag else None
  c|={'layout':all(x in t for x in RANGES+['Preencha seus dados e veja as parcelas:','VER PARCELAS','Pular, quero ver as ofertas','Aceito receber ofertas por SMS.']),
      'skip_loading':'"skipLoading":true' in t and '"loadingMs":0' in t,
      'optional':'"optional":true' in t and '"consentEnabled":true' in t,
      'legal':len(links)==3,
      'direct_reward':'submitSmsLead(ctaButton, false)' in t and 'triggerTrustedRewarded(ctaButton)' in t,
      'provider_direct':(('window.jbftag.showRewardedAds(safeCloseQuiz)' in t) if provider=='jbf' else ('id="mgs-cf-sms-skip" class="pg-rewarded"' in t if provider=='m2' else 'id="mgs-cf-sms-skip" class="av-rewarded"' in t and 'mgsHandleSmsSkipReward' in t)),
      'hero':bool(img)}
  extras={'links':[urljoin(r.url,x) for x in links],'hero':urljoin(r.url,img.group(1)) if img else ''}
 else:
  c|={'legacy_no_sms':'id="mgs-cf-sms-form"' not in t and 'id="mgs-cf-sms-skip"' not in t}
 return {'site':site,'kind':kind,'provider':provider,'checks':c,'extras':extras,'pass':all(c.values())}

def asset_check(url):
 r=get(url);soft404='error404' in r.text[:5000].lower() if 'text/html' in r.headers.get('content-type','') else False
 return {'url':url,'http':r.status_code,'content_type':r.headers.get('content-type',''),'pass':r.status_code==200 and not soft404}

def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  rows=list(ex.map(lambda x:validate_route(*x),[(s,k) for s in SITES for k in ('sms','legacy')]))
 urls=[]
 for x in rows:
  if x['kind']=='sms':urls.extend(x['extras']['links']+[x['extras']['hero']])
 urls=sorted(set(u for u in urls if u))
 with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:assets=list(ex.map(asset_check,urls))
 summary={'routes_pass':sum(x['pass'] for x in rows),'routes_total':len(rows),'assets_pass':sum(x['pass'] for x in assets),'assets_total':len(assets),'providers':{'actview':sum(x['provider']=='actview' for x in rows),'m2':sum(x['provider']=='m2' for x in rows),'jbf':sum(x['provider']=='jbf' for x in rows)}}
 out={'summary':summary,'routes':rows,'assets':assets,'pass':all(x['pass'] for x in rows+assets)}
 print(json.dumps(out,ensure_ascii=False,indent=2))
 if not out['pass']:raise SystemExit(1)
if __name__=='__main__':main()
