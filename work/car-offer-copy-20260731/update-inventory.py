#!/usr/bin/env python3
import json
from pathlib import Path
p=Path('/root/mgs-agent/data/infra-inventory.json')
d=json.loads(p.read_text())
now='2026-07-31T19:00:35+00:00'
arts=d['runtime_artifacts']
plugin=next(x for x in arts if x.get('name')=='mgs-chat-funnels')
plugin.update({'files_count':9,'size_bytes':654311,'sha256_manifest':'937105d077d014913ee3a2753623a4365da0a90154233e21a51f4245a03ea558','modified_at':now,'source_report':'REPORT-INFRA CAR-BR offer-copy 8-site rollout 2026-07-31'})
validation='Offer-copy rollout 2026-07-31: 8/8 sites and 16/16 legacy+SMS routes HTTP 200 with exact screenshot copy; 48/48 own-domain targets, UTM/fbclid merge, provider split and private SMS URL absence preserved; browser Eggbev reached three visible cards without overlap and retained UTMs/fbclid.'
if validation not in plugin.setdefault('validations',[]): plugin['validations'].append(validation)
for b in ['/var/backups/mgs-chat-funnels-offer-copy/20260731T185016Z/zuout.com','/var/backups/mgs-chat-funnels-offer-copy/20260731T185100Z','/root/mgs-agent/backups/car-offer-copy/20260731T185115Z']:
 if b not in plugin.setdefault('backup_paths',[]): plugin['backup_paths'].append(b)

legacy=next(x for x in arts if x.get('id')=='zuout-mgs-chat-funnels-car-br-config')
legacy.update({'sha256':'8bd40fd9169cc18e68facccb991ee60aa33108c97e53787069a21538268d24d1','size_bytes':4780,'purpose':'Zuout CAR-BR-01 legacy config with the fleet-standard three-card offer copy requested by Rodolfo; own-domain targets and ActView preserved.','validation':'Exact runtime readback; screenshot copy present; 3/3 targets remain zuout.com; /chat/car/br1 HTTP 200; ActView and UTM/fbclid merge preserved.','backup_path':'/var/backups/mgs-chat-funnels-offer-copy/20260731T185016Z/zuout.com/car-br-01.json','updated_at':now})
sms=next(x for x in arts if x.get('id')=='zuout-mgs-chat-funnels-car-br-sms-config-20260731')
sms.update({'sha256':'7f68cfb031dc352899a296182ca9252d22957d61ef9b9cc3f1ec1e27ad746571','size_bytes':5625,'purpose':'Zuout CAR-BR-01-SMS optional lead gate plus fleet-standard three-card offer copy requested by Rodolfo; G002, own-domain targets and ActView preserved.','validation':'Exact runtime readback; screenshot copy present; G002 and 3/3 zuout.com targets preserved; /chat-sms/car/br1 HTTP 200; trusted-click rewarded code and UTM/fbclid merge preserved.','backup_path':'/var/backups/mgs-chat-funnels-offer-copy/20260731T185016Z/zuout.com/car-br-01-sms.json','updated_at':now})

entry={
 'id':'mgs-chat-car-br-offer-copy-rollout-20260731','agent':'zeus','type':'wordpress_plugin_config_rollout','authorized_by':'Rodolfo Mattei','discord_message_id':'1532821383137198151','status':'completed_validated','updated_at':now,
 'scope':{'sites':['zuout.com','zytiva.com','openzed.com','finance.topfeed.fun','newsoun.com','wantabrand.com','cliquet.com','eggbev.com'],'configs':['CAR-BR-01','CAR-BR-01-SMS'],'routes':['/chat/car/br1','/chat-sms/car/br1']},
 'copy':[
  {'name':'🚗 Financiar sem entrada','subtitle':'Valores com parcelas','bank':'R$157,00 a R$299,00'},
  {'name':'💰 Ver ofertas disponíveis','subtitle':'Bancos com taxas reduzidas','bank':'e facilidade para baixo score.'},
  {'name':'🚘 Financiamento com parcela baixa','subtitle':'Consulte se essa condição está disponível para você,','bank':'Oferta por tempo LIMITADO !'}],
 'changed_runtime_fields':['offers.0.name','offers.1.name','offers.2.name','offers.2.subtitle'],
 'preserved':['all offer targets/URLs','site provider split (JBF 6, Wantabrand M2/PubGuru 1, Zuout ActView 1)','UTM/fbclid merge','SMS manager mapping and private endpoints','all non-copy config fields'],
 'canonical_config':{'path':'/root/mgs-agent/plugins/mgs-chat-funnels/configs/car-br-01.json','sha256':'585c80e525d4abed9175cb21eeebf45ed51cf5c6b5380e81412312230d38f4fb','size_bytes':5192},
 'runcloud_config_hashes':{
  'eggbev.com':{'legacy':'b89b86f679572823cb6a62f4c16a6f976e55fde7f06aa5766f62f16f46c851c2','sms':'672e91fe0314c9d809c8d2947ad01eadae6c87bb817e022f99cafbfd82578f5c'},
  'newsoun.com':{'legacy':'ea3bbaa0e4988743181275d9db0a63c6ab0a7240b20532f9345d8a4cf8963529','sms':'cabd00c01e0127dd0b50e06f449a86b883ab7169b7cca64a5ed19a10386df086'},
  'finance.topfeed.fun':{'legacy':'9e4a66fe91bc7cb08926a643a6497f13d03eb8c3387b746a2033e9a8fa98e002','sms':'918947d4f602f50eaad52e7bda91e909056ed4492499e13be017f75d169ed954'},
  'wantabrand.com':{'legacy':'1c4ffbf43fb0bc75423df58cf879de7abb538c3343c42d2048a6c67622002546','sms':'a78e3499794896724c72881fcf7305e1ff86b083cec1221a92090be19450f46f'},
  'zuout.com':{'legacy':'8bd40fd9169cc18e68facccb991ee60aa33108c97e53787069a21538268d24d1','sms':'7f68cfb031dc352899a296182ca9252d22957d61ef9b9cc3f1ec1e27ad746571'},
  'zytiva.com':{'legacy':'592627fa50dea36db7d918c855ddebcaf018ba59b8437ff31da811cd531e39ca','sms':'1118a3b4e7c1250552a59783420bf40ba467892cf1dd5d4f71d8f022f5ecf46e'}},
 'bitnami_normalized_config_hashes':{
  'openzed.com':{'legacy':'6e0b031c26c406ec35845a2cdbbba2303c35993ad77163929296848ae0f17448','sms':'f07bc36d1e39c6b6ce450145e287d21e8172d4bae87b1204ac8699bfcfb3da93'},
  'cliquet.com':{'legacy':'8709bceae322d70a8c1b90b4a25b0d6fd79d4e1a6e552921439ee70d1ed2f97c','sms':'83bcb3e6d29ffeda0d5426857888ebd42b0de3a06dc5f82784e47dfda0ed4443'}},
 'backups':['/var/backups/mgs-chat-funnels-offer-copy/20260731T185016Z/zuout.com','/var/backups/mgs-chat-funnels-offer-copy/20260731T185100Z','/root/mgs-agent/backups/car-offer-copy/20260731T185115Z'],
 'validation':{'exact_config_readback':'16/16','public_http_200':'16/16','exact_copy':'16/16','own_domain_targets':'48/48','providers_preserved':'8/8','utm_fbclid_merge':'16/16','private_sms_urls_absent':'16/16','browser_visual':'Eggbev legacy: 3 cards visible and legible, no overlap; destination links preserved cb+utm_source+utm_medium+fbclid'},
 'known_warning':'Wantabrand WP-CLI emitted its pre-existing yoast-rest-meta.php permission warning; mutation, JSON validation, exact config readback and both public routes passed.'
}
arts[:]=[x for x in arts if x.get('id')!=entry['id']]
arts.append(entry)
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(entry['id'],entry['status'],len(arts))
