#!/usr/bin/env python3
import json
from pathlib import Path

path = Path('/root/mgs-agent/data/infra-inventory.json')
data = json.loads(path.read_text())
artifacts = data['runtime_artifacts']
now = '2026-07-31T14:03:42-04:00'
backup = '/home/runcloud/zeus-backups/zuout-chat-sms-20260731134609'

main = next(x for x in artifacts if x.get('type') == 'wordpress_plugin' and x.get('name') == 'mgs-chat-funnels')
main.update({
    'version': '0.4.3',
    'status': 'canonical_0.4.3_zuout_sms_canary_active_other_7_sites_0.4.2',
    'files_count': 9,
    'size_bytes': 650597,
    'sha256_manifest': '36006a3646162a735b21a903728b097df09f3215b9d426402f38155bb899ce2e',
    'package_path': '/root/mgs-agent/work/zuout-chat-sms-fincfrog-20260731/mgs-chat-funnels-0.4.3-code-only-final.zip',
    'package_sha256': '4968d1082b1db26d2a5a5281087dbe387c82ee22f52bdc75b735d6e75320c3f0',
    'modified_at': '2026-07-31T18:03:42+00:00',
    'source_report': 'REPORT-INFRA Zuout optional SMS/geo canary 2026-07-31',
    'description': 'Canonical v0.4.3 adds config-gated optional SMS capture, preselected visible consent, IP city/region social proof, vehicle image, direct gate-to-form transition, discreet legal footer and ActView-safe skip/replay. Deployed only to the Zuout CAR-BR SMS canary; the other seven sites remain on v0.4.2 pending approval.',
    'deployment_versions': {
        'zuout.com': '0.4.3',
        'zytiva.com': '0.4.2',
        'openzed.com': '0.4.2',
        'finance.topfeed.fun': '0.4.2',
        'newsoun.com': '0.4.2',
        'wantabrand.com': '0.4.2',
        'cliquet.com': '0.4.2',
        'eggbev.com': '0.4.2',
    },
})
for evidence in [
    'Zuout v0.4.3 canary: price-range gate, IP city/region, vehicle image, no visible loading, prechecked consent, optional skip and discreet legal footer validated in browser.',
    'Skip and unchecked-consent paths created no REST lead request, registered ActView zout_rewarded and continued to the chat; frontend mocked-success path preserved UTMs/fbclid and sms_consent=yes.',
    'ActView runtime validated: one scr.actview.net/zuout.js, zero JBF, rewarded CTA class-only anchor after capture/skip, zout_top_wrapper/zout_top inserted, no PubGuru tag on Zuout, offer cards have no av-rewarded class.',
    'Transactional backend smoke intercepted outbound SMS, produced HTTP 200 ok:G002 with lead count 0→1→0 and no real SMS; legacy /chat/car/br1 config hash remained unchanged.',
]:
    if evidence not in main.setdefault('validations', []): main['validations'].append(evidence)
if backup not in main.setdefault('backup_paths', []): main['backup_paths'].append(backup)

plugin = next(x for x in artifacts if x.get('id') == 'zuout-mgs-chat-funnels-plugin')
plugin.update({
    'sha256': 'a39f3c019f484e4cc648336d4ca8e2d4145e2a2d986cc780ca7be57b55acd0c9',
    'size_bytes': 93230,
    'purpose': 'Zuout MGS Chat Funnels v0.4.3 plugin renderer and admin support for optional SMS/consent, geo, vehicle image, compact gate and legal footer while preserving ActView.',
    'validation': 'PHP lint OK; plugin active v0.4.3; public SMS and legacy routes HTTP 200; admin renderer contains all new controls; exact runtime hash read back.',
    'backup_path': backup + '/mgs-chat-funnels-pre-0.4.3.tgz',
    'updated_at': now,
})

legacy = next(x for x in artifacts if x.get('id') == 'zuout-mgs-chat-funnels-car-br-config')
legacy.update({
    'sha256': 'fb7a7d83afcc11485ed8bd394c7b40435b35ec5392620694b40da75c50f07bb4',
    'size_bytes': 4783,
    'purpose': 'Zuout CAR-BR-01 legacy chat config preserved unchanged while the SMS-only canary was revised.',
    'validation': 'Exact pre/post hash unchanged; /chat/car/br1 HTTP 200; original gate and offers preserved; ActView only, no JBF.',
    'backup_path': backup + '/mgs-chat-funnels-pre-0.4.3.tgz',
    'updated_at': now,
})

template = next(x for x in artifacts if x.get('id') == 'zuout-mgs-chat-funnels-template')
template.update({
    'sha256': '4f776ad587bbb83250e67d0837e7cb2cbfc1a5b0286bbb8e0b864018d3612d6e',
    'size_bytes': 45578,
    'purpose': 'Config-gated chat template for Zuout v0.4.3, including optional SMS paths and isolated ActView rewarded/top-ad behavior.',
    'validation': 'Node syntax OK; skip and unchecked consent continue without REST submit; mocked lead success replays class-only ActView CTA; zout_top_wrapper/zout_top created; offer cards remain free of av-rewarded; zero browser JS errors.',
    'backup_path': backup + '/ciro-index-template-before-actview-top-20260731135755.html',
    'updated_at': now,
})

new_id = 'zuout-mgs-chat-funnels-car-br-sms-config-20260731'
new_artifact = {
    'id': new_id,
    'agent': 'zeus',
    'type': 'wordpress_plugin_config',
    'path': '/home/runcloud/webapps/zuout/wp-content/plugins/mgs-chat-funnels/configs/car-br-01-sms.json',
    'sha256': '7e5e4eeb6a15d023ad4b3a57438a5ed185a83900de61d8de71e45169ff134f53',
    'size_bytes': 5628,
    'source': 'RunCloud Inc01 zuout.com',
    'purpose': 'ZUOUT CAR-BR-01-SMS canary: price-range gate, geo, default vehicle image, optional confirmed SMS capture, prechecked consent, skip, compact form and legal footer.',
    'validation': 'Config readback exact; G002 preserved; three own-domain P1 targets preserved; browser skip/unchecked paths sent no lead; mocked frontend and backend transaction passed; private SMS endpoint absent from public HTML.',
    'backup_path': backup + '/mgs-chat-funnels-pre-0.4.3.tgz',
    'updated_at': now,
}
for i, item in enumerate(artifacts):
    if item.get('id') == new_id:
        artifacts[i] = new_artifact
        break
else:
    artifacts.append(new_artifact)

path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
print('inventory_updated')
