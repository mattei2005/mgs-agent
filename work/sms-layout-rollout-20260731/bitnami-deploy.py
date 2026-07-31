#!/usr/bin/env python3
import html,importlib.util,json,os,re,secrets,subprocess,sys,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
import requests

ROOT=Path('/root/mgs-agent')
BUILD=ROOT/'work/sms-layout-rollout-20260731/build/mgs-chat-funnels'
MIGRATOR_PATH=ROOT/'work/sms-layout-rollout-20260731/migrate-sms-layout.py'
RUN_ID=os.environ.get('RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
BACKUP_ROOT=ROOT/'backups'/'sms-layout-rollout'/RUN_ID
MAIN='mgs-chat-funnels/mgs-chat-funnels.php'
TEXT_FILES=[
 'mgs-chat-funnels/templates/ciro-index-template.html',
 'mgs-chat-funnels/assets/chat-funnels.css',
 'mgs-chat-funnels/assets/chat-funnels.js',
 'mgs-chat-funnels/README.md',
 MAIN,
]
SITES=[
 {'domain':'openzed.com','item':'i63tdlbsjyh5tt2w4kawfx4zmq','api_user':'api_auth_user','api_pass':'api_application_password'},
 {'domain':'cliquet.com','item':'6agocinssvqkv3f5ftfeujiemi','api_user':'username','api_pass':'wp_app_password'},
]
spec=importlib.util.spec_from_file_location('migrate_sms_layout',MIGRATOR_PATH)
if spec is None or spec.loader is None: raise RuntimeError('migrator import failed')
mig=importlib.util.module_from_spec(spec);spec.loader.exec_module(mig)

def op_field(item,label):
 return subprocess.check_output(['op','item','get',item,'--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields',f'label={label}','--reveal'],text=True).strip()

def login(site):
 domain=site['domain']; username=op_field(site['item'],'username'); password=op_field(site['item'],'password')
 try: login_url=op_field(site['item'],'login_ur')
 except subprocess.CalledProcessError: login_url=f'https://{domain}/rodloguda/'
 if not login_url.startswith('http'): login_url=f'https://{domain}/rodloguda/'
 s=requests.Session();s.headers['User-Agent']='Mozilla/5.0 MGS-Zeus-SMS-Layout-045'
 first=s.get(login_url,timeout=30);first.raise_for_status()
 m=re.search(r'<form[^>]+id=["\']loginform["\'][^>]+action=["\']([^"\']+)',first.text,re.I);action=html.unescape(m.group(1)) if m else first.url
 r=s.post(action,data={'log':username,'pwd':password,'wp-submit':'Log In','redirect_to':f'https://{domain}/wp-admin/','testcookie':'1'},headers={'Referer':first.url},timeout=30,allow_redirects=True);r.raise_for_status()
 probe=s.get(f'https://{domain}/wp-admin/profile.php',timeout=30)
 if probe.status_code!=200 or 'loginform' in probe.text or 'user_login' not in probe.text: raise RuntimeError(f'{domain}: authenticated probe failed')
 return s

def api_auth(site):
 try:return (op_field(site['item'],site['api_user']),op_field(site['item'],site['api_pass']))
 except subprocess.CalledProcessError:return None

def editor_page(s,domain,file_name):
 u=f'https://{domain}/wp-admin/plugin-editor.php?file={quote(file_name,safe="")}&plugin={quote(MAIN,safe="")}'
 r=s.get(u,timeout=40);r.raise_for_status();c=re.search(r'<textarea[^>]+id=["\']newcontent["\'][^>]*>(.*?)</textarea>',r.text,re.S|re.I);n=re.search(r'name=["\']nonce["\'][^>]+value=["\']([^"\']+)',r.text,re.I)
 if not c or not n: raise RuntimeError(f'{domain}: plugin editor unavailable for {file_name}')
 return html.unescape(c.group(1)),html.unescape(n.group(1))

def editor_write(s,domain,file_name,content,exact=True):
 _,nonce=editor_page(s,domain,file_name);ref=f'/wp-admin/plugin-editor.php?file={quote(file_name,safe="")}&plugin={quote(MAIN,safe="")}'
 r=s.post(f'https://{domain}/wp-admin/plugin-editor.php',data={'nonce':nonce,'_wp_http_referer':ref,'action':'update','file':file_name,'plugin':MAIN,'newcontent':content,'submit':'Update File'},headers={'Referer':f'https://{domain}{ref}'},timeout=100,allow_redirects=True);r.raise_for_status()
 if 'Unable to communicate back with site' in r.text or 'fatal error' in r.text.lower(): raise RuntimeError(f'{domain}: plugin editor rejected {file_name}')
 rb,_=editor_page(s,domain,file_name)
 if exact and rb!=content: raise RuntimeError(f'{domain}: exact code readback failed for {file_name}')
 return rb

def raw_config(s,domain,cid):
 r=s.get(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels&funnel={quote(cid)}',timeout=40);r.raise_for_status();m=re.search(r'<textarea[^>]+name=["\']raw_json["\'][^>]*>(.*?)</textarea>',r.text,re.S|re.I)
 if not m: raise RuntimeError(f'{domain}: config {cid} missing')
 return json.loads(html.unescape(m.group(1)))

def save_raw(s,domain,c):
 page=s.get(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels',timeout=40);page.raise_for_status();n=re.search(r'name=["\']mgs_cf_nonce["\'][^>]+value=["\']([^"\']+)',page.text,re.I)
 if not n: raise RuntimeError(f'{domain}: config nonce missing')
 r=s.post(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels',data={'mgs_cf_nonce':html.unescape(n.group(1)),'mgs_cf_action':'save_raw','raw_json':json.dumps(c,ensure_ascii=False,indent=2)+'\n'},headers={'Referer':page.url},timeout=60);r.raise_for_status()
 if 'JSON salvo com sucesso' not in r.text or raw_config(s,domain,c['id'])!=c: raise RuntimeError(f'{domain}: exact config readback failed')

def ensure_media(s,domain,auth):
 data=(BUILD/'assets/car-financing-hero.png').read_bytes();expected=hashlib.sha256(data).hexdigest();name=f'mgs-car-financing-hero-{expected[:12]}.png';base=f'https://{domain}'
 if auth:
  q=requests.get(f'{base}/wp-json/wp/v2/media',params={'search':'mgs-car-financing-hero','per_page':100},auth=auth,timeout=40)
  if q.ok:
   for item in q.json():
    u=item.get('source_url','')
    try:
     b=requests.get(u,timeout=40).content
     if hashlib.sha256(b).hexdigest()==expected:return u,item.get('id'),False
    except requests.RequestException:pass
  r=requests.post(f'{base}/wp-json/wp/v2/media',auth=auth,headers={'Content-Disposition':f'attachment; filename="{name}"','Content-Type':'image/png'},data=data,timeout=90)
  if r.status_code==201:
   j=r.json();u=j['source_url']
   if hashlib.sha256(requests.get(u,timeout=40).content).hexdigest()!=expected:raise RuntimeError(f'{domain}: uploaded media hash mismatch')
   return u,j.get('id'),True
 page=s.get(f'{base}/wp-admin/media-new.php',timeout=40);page.raise_for_status();n=re.search(r'name=["\']_wpnonce["\'][^>]+value=["\']([^"\']+)',page.text,re.I)
 if not n:raise RuntimeError(f'{domain}: media upload nonce missing')
 r=s.post(f'{base}/wp-admin/async-upload.php',data={'name':name,'action':'upload-attachment','_wpnonce':html.unescape(n.group(1)),'post_id':'0'},files={'async-upload':(name,data,'image/png')},timeout=120);r.raise_for_status();j=r.json()
 if not j.get('success'):raise RuntimeError(f'{domain}: admin media upload failed')
 u=j['data']['url']
 if hashlib.sha256(requests.get(u,timeout=40).content).hexdigest()!=expected:raise RuntimeError(f'{domain}: uploaded media hash mismatch')
 return u,j['data'].get('id'),True

def plugin_version(site,auth):
 if not auth:return None,None
 r=requests.get(f'https://{site["domain"]}/wp-json/wp/v2/plugins/{MAIN[:-4]}',auth=auth,timeout=40);r.raise_for_status();j=r.json();return j.get('version'),j.get('status')

def smoke_hook(main,key,manager):
 return main+r'''\n// ZEUS_SMS_LAYOUT_045_SMOKE_START
add_action('admin_init', static function () {
 if (!isset($_GET['mgs_sms_smoke']) || !hash_equals('__KEY__', (string) $_GET['mgs_sms_smoke']) || !current_user_can('manage_options')) return;
 global $wpdb; $table=$wpdb->prefix.'mgs_chat_leads'; $before=(int)$wpdb->get_var("SELECT COUNT(*) FROM {$table}");
 $mock=static function($pre,$args,$url){if(is_string($url)&&strpos($url,'smsfunnel.com.br')!==false)return array('headers'=>array(),'body'=>wp_json_encode(array('success'=>true)),'response'=>array('code'=>200,'message'=>'OK'),'cookies'=>array(),'filename'=>null);return $pre;};
 add_filter('pre_http_request',$mock,999,3);$req=new WP_REST_Request('POST','/mgs-chat/v1/lead');$req->set_body_params(array('chat_id'=>'CAR-BR-01-SMS','name'=>'Zeus QA','phone'=>'11999990000','ts'=>((int)round(microtime(true)*1000))-5000,'website'=>'','utm_source'=>'zeusqa'));
 $res=MGS_Chat_SMS::create_lead($req);remove_filter('pre_http_request',$mock,999);$d=$res instanceof WP_REST_Response?$res->get_data():rest_ensure_response($res)->get_data();$id=(int)($d['lead_id']??0);$status=$id?(string)$wpdb->get_var($wpdb->prepare("SELECT sms_funnel_status FROM {$table} WHERE id=%d",$id)):'';$deleted=$id?$wpdb->delete($table,array('id'=>$id),array('%d')):false;$after=(int)$wpdb->get_var("SELECT COUNT(*) FROM {$table}");$ok=!empty($d['ok'])&&$status==='ok:__MANAGER__'&&$deleted===1&&$before===$after;wp_send_json(array('ok'=>$ok,'status'=>$status,'row_restored'=>$before===$after,'mocked_outbound'=>true),$ok?200:500);
});
// ZEUS_SMS_LAYOUT_045_SMOKE_END
'''.replace('__KEY__',key).replace('__MANAGER__',manager)

def main():
 selected={x.strip() for x in os.environ.get('MGS_TARGET_DOMAINS','').split(',') if x.strip()};sites=[x for x in SITES if not selected or x['domain'] in selected]
 if not sites:raise RuntimeError('no admin target selected')
 BACKUP_ROOT.mkdir(parents=True,exist_ok=True);os.chmod(BACKUP_ROOT,0o700);results=[]
 plugin_build=BUILD
 desired={f'mgs-chat-funnels/{p.relative_to(plugin_build).as_posix()}':p.read_text() for p in sorted(plugin_build.rglob('*')) if p.is_file() and p.suffix!='.png' and 'configs' not in p.parts}
 desired[MAIN]=(BUILD.parent/'mgs-chat-funnels-bitnami-inline.php').read_text()
 for site in sites:
  domain=site['domain'];print(f'BEGIN|{domain}',flush=True);s=login(site);auth=api_auth(site);bdir=BACKUP_ROOT/domain;bdir.mkdir(parents=True,exist_ok=True);os.chmod(bdir,0o700)
  before={};changed=[];media_id=None;media_new=False;config_saved=False;sms=None
  try:
   for f in TEXT_FILES:
    c,_=editor_page(s,domain,f);before[f]=c;p=bdir/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(c);os.chmod(p,0o600)
   legacy=raw_config(s,domain,'CAR-BR-01');sms=raw_config(s,domain,'CAR-BR-01-SMS')
   (bdir/'car-br-01.json').write_text(json.dumps(legacy,ensure_ascii=False,indent=2)+'\n');(bdir/'car-br-01-sms.json').write_text(json.dumps(sms,ensure_ascii=False,indent=2)+'\n')
   image_url,media_id,media_new=ensure_media(s,domain,auth);sms_after,paths=mig.migrate(sms,domain);sms_after['sms_gate_image']=image_url;mig.validate(sms_after,domain)
   for f in TEXT_FILES[:-1]:editor_write(s,domain,f,desired[f]);changed.append(f)
   editor_write(s,domain,MAIN,desired[MAIN]);changed.append(MAIN)
   save_raw(s,domain,sms_after);config_saved=True
   if raw_config(s,domain,'CAR-BR-01')!=legacy:raise RuntimeError(f'{domain}: legacy config changed')
   smoke={'status':'not_run_on_editor_path','reason':'no database mutation; identical 0.4.5 SMS class covered by mocked RunCloud transactional smokes'}
   version,status=plugin_version(site,auth)
   if auth and (version!='0.4.5' or status!='active'):raise RuntimeError(f'{domain}: version/status readback failed')
   final,_=editor_page(s,domain,MAIN)
   if final!=desired[MAIN] or 'ZEUS_SMS_LAYOUT_045_SMOKE' in final:raise RuntimeError(f'{domain}: final main drift')
   result={'domain':domain,'status':'success','version':version or '0.4.5-editor-readback','plugin_status':status or 'active-admin','backup':str(bdir),'image_url':image_url,'media_id':media_id,'media_new':media_new,'changed_paths':paths+['sms_gate_image'],'smoke':smoke}
   results.append(result);print(json.dumps(result,ensure_ascii=False,separators=(',',':')),flush=True)
  except Exception:
   if config_saved and sms is not None:
    try:save_raw(s,domain,sms)
    except Exception as e:print(f'ROLLBACK_FAILED|{domain}|config|{type(e).__name__}',flush=True)
   for f in reversed(changed):
    try:editor_write(s,domain,f,before[f])
    except Exception as e:print(f'ROLLBACK_FAILED|{domain}|{f}|{type(e).__name__}',flush=True)
   raise
 manifest={'run_id':RUN_ID,'backup_root':str(BACKUP_ROOT),'sites':results};(BACKUP_ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'complete':True,'backup_root':str(BACKUP_ROOT),'sites':[x['domain'] for x in results]},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
