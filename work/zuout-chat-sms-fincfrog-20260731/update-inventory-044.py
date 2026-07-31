#!/usr/bin/env python3
import json
from pathlib import Path
p=Path('/root/mgs-agent/data/infra-inventory.json')
d=json.loads(p.read_text())
now='2026-07-31T18:39:10+00:00'
by_id={x.get('id'):x for x in d['runtime_artifacts'] if x.get('id')}
plugin=next(x for x in d['runtime_artifacts'] if x.get('name') == 'mgs-chat-funnels')
plugin.update({
 'version':'0.4.4',
 'status':'canonical_0.4.4_zuout_sms_canary_active_other_7_sites_0.4.2',
 'size_bytes':654316,
 'sha256_manifest':'17a5cff4eabf0121b016ec4ccc3879a2000fe28f5a518ad483879e66f9cd500d',
 'package_path':'/root/mgs-agent/work/zuout-chat-sms-fincfrog-20260731/mgs-chat-funnels-0.4.4-code-only.zip',
 'package_sha256':'b2fa4238f48dd23df8c375cab21af87f9b8a3633c46fa842b8553616658104f4',
 'modified_at':now,
 'source_report':'REPORT-INFRA Zuout direct trusted-click rewarded correction 2026-07-31',
 'description':'Canonical v0.4.4 keeps the optional CAR-BR SMS gate and triggers Zuout ActView rewarded from the original trusted user click while WordPress/SMS submission runs asynchronously. Deployed only to Zuout; the other seven sites remain on v0.4.2.',
 'deployment_versions':{'zuout.com':'0.4.4','zytiva.com':'0.4.2','openzed.com':'0.4.2','finance.topfeed.fun':'0.4.2','newsoun.com':'0.4.2','wantabrand.com':'0.4.2','cliquet.com':'0.4.2','eggbev.com':'0.4.2'}
})
if '/home/runcloud/zeus-backups/zuout-chat-sms-reward-direct-20260731183047' not in plugin.setdefault('backup_paths',[]):
 plugin['backup_paths'].append('/home/runcloud/zeus-backups/zuout-chat-sms-reward-direct-20260731183047')
plugin.setdefault('validations',[]).append('Zuout 0.4.4: pre-change proof showed skip used trusted skip click followed by untrusted programmatic CTA replay and did not print rewarded reliably. Post-change click is trusted directly on av-rewarded; zout_rewarded GPT iframe reached 1280x577 on skip; valid submit registers rewarded without waiting for the WordPress/SMS response; no JS errors.')
main=by_id['zuout-mgs-chat-funnels-plugin']
main.update({'size_bytes':93259,'sha256':'6233fdffe9abb17bcc805921643e6a752e0a06ed2dc81b9c669337a013748435','purpose':'Zuout active MGS Chat Funnels bootstrap/router, version 0.4.4; direct trusted-click ActView rewarded without waiting for lead response.','validation':'PHP lint; WP plugin version 0.4.4 active; remote hash readback; config preserved; public direct-click smoke passed.','backup_path':'/home/runcloud/zeus-backups/zuout-chat-sms-reward-direct-20260731183047/mgs-chat-funnels-pre-0.4.4.tgz','updated_at':now})
sms=by_id.get('zuout-mgs-chat-funnels-sms-engine')
if sms is None:
 sms={'id':'zuout-mgs-chat-funnels-sms-engine','agent':'zeus','type':'wordpress_plugin_component','path':'/home/runcloud/webapps/zuout/wp-content/plugins/mgs-chat-funnels/includes/class-mgs-chat-sms.php','source':'RunCloud Inc01 zuout.com'}
 d['runtime_artifacts'].append(sms)
sms.update({'size_bytes':32149,'sha256':'22bb98b1064ce5223109e28af2ed6ae45078f3a71e4bfe3d464157630965bc91','purpose':'Zuout SMS lead helper; ActView skip renders as direct class-only trusted rewarded anchor.','validation':'PHP lint; remote hash readback; skip remains zero-lead while triggering direct trusted rewarded.','backup_path':'/home/runcloud/zeus-backups/zuout-chat-sms-reward-direct-20260731183047/mgs-chat-funnels-pre-0.4.4.tgz','updated_at':now})
tpl=by_id['zuout-mgs-chat-funnels-template']
tpl.update({'size_bytes':48956,'sha256':'81a99fa94900985f46c44738575ceb6aa19543fef62c2b41653f69d8ae86b1cd','purpose':'Zuout funnel template with dynamic ActView eligibility, direct trusted rewarded click, asynchronous lead send, chat, separate top placement and offers.','validation':'Inline JS syntax; invalid CTA clean; eligible CTA/skip class-only av-rewarded before click; one trusted click with no untrusted replay; zout_rewarded slot/iframe printed; zero JS errors.','backup_path':'/home/runcloud/zeus-backups/zuout-chat-sms-reward-direct-20260731183047/mgs-chat-funnels-pre-0.4.4.tgz','updated_at':now})
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('updated',plugin['version'],main['sha256'],sms['sha256'],tpl['sha256'])
