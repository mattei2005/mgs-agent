#!/usr/bin/env python3
import copy
import html
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

ROOT = Path('/root/mgs-agent')
PLUGIN = ROOT / 'plugins/mgs-chat-funnels'
WORK = ROOT / 'work/chat-sms-rollout-20260716'
BACKUP_ROOT = Path('/root/mgs-agent-backups/chat-sms-rollout') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
MAIN_PLUGIN = 'mgs-chat-funnels/mgs-chat-funnels.php'
FILES = [
    'mgs-chat-funnels/assets/chat-funnels.js',
    'mgs-chat-funnels/assets/chat-funnels.css',
    'mgs-chat-funnels/templates/ciro-index-template.html',
    MAIN_PLUGIN,
]
SITES = [
    {'domain': 'openzed.com', 'item': 'i63tdlbsjyh5tt2w4kawfx4zmq', 'api_user': 'api_auth_user', 'api_pass': 'api_application_password'},
    {'domain': 'cliquet.com', 'item': '6agocinssvqkv3f5ftfeujiemi', 'api_user': 'username', 'api_pass': 'wp_app_password'},
]


def op_field(item, label):
    return subprocess.check_output([
        'op', 'item', 'get', item, '--vault', 'MGS Conteúdo',
        '--fields', f'label={label}', '--reveal'
    ], text=True).strip()


def login(site):
    domain = site['domain']
    username = op_field(site['item'], 'username')
    password = op_field(site['item'], 'password')
    login_url = op_field(site['item'], 'login_ur')
    if not login_url.startswith('http'):
        login_url = f'https://{domain}/rodloguda/'
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 MGS-Zeus-Bitnami-Rollout'
    first = session.get(login_url, timeout=30)
    first.raise_for_status()
    match = re.search(r'<form[^>]+id=["\']loginform["\'][^>]+action=["\']([^"\']+)', first.text, re.I)
    action = html.unescape(match.group(1)) if match else first.url
    response = session.post(action, data={
        'log': username,
        'pwd': password,
        'wp-submit': 'Log In',
        'redirect_to': f'https://{domain}/wp-admin/',
        'testcookie': '1',
    }, headers={'Referer': first.url}, timeout=30, allow_redirects=True)
    response.raise_for_status()
    probe = session.get(f'https://{domain}/wp-admin/profile.php', timeout=30)
    if probe.status_code != 200 or 'loginform' in probe.text or 'user_login' not in probe.text:
        raise RuntimeError(f'{domain}: authenticated wp-admin probe failed')
    return session


def editor_page(session, domain, file_name):
    url = (f'https://{domain}/wp-admin/plugin-editor.php?file={quote(file_name, safe="")}'
           f'&plugin={quote(MAIN_PLUGIN, safe="")}')
    response = session.get(url, timeout=35)
    response.raise_for_status()
    content = re.search(r'<textarea[^>]+id=["\']newcontent["\'][^>]*>(.*?)</textarea>', response.text, re.S | re.I)
    nonce = re.search(r'name=["\']nonce["\'][^>]+value=["\']([^"\']+)', response.text, re.I)
    if not content or not nonce:
        raise RuntimeError(f'{domain}: plugin editor unavailable for {file_name}')
    return html.unescape(content.group(1)), html.unescape(nonce.group(1))


def editor_write(session, domain, file_name, new_content):
    _, nonce = editor_page(session, domain, file_name)
    referer = (f'/wp-admin/plugin-editor.php?file={quote(file_name, safe="")}'
               f'&plugin={quote(MAIN_PLUGIN, safe="")}')
    response = session.post(f'https://{domain}/wp-admin/plugin-editor.php', data={
        'nonce': nonce,
        '_wp_http_referer': referer,
        'action': 'update',
        'file': file_name,
        'plugin': MAIN_PLUGIN,
        'newcontent': new_content,
        'submit': 'Update File',
    }, headers={'Referer': f'https://{domain}{referer}'}, timeout=90, allow_redirects=True)
    response.raise_for_status()
    if 'Unable to communicate back with site' in response.text or 'fatal error' in response.text.lower():
        raise RuntimeError(f'{domain}: plugin editor rejected {file_name}')
    readback, _ = editor_page(session, domain, file_name)
    if readback != new_content:
        raise RuntimeError(f'{domain}: exact plugin editor readback failed for {file_name}')


def raw_config(session, domain, config_id):
    url = f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels&funnel={quote(config_id)}'
    response = session.get(url, timeout=35)
    response.raise_for_status()
    match = re.search(r'<textarea[^>]+name=["\']raw_json["\'][^>]*>(.*?)</textarea>', response.text, re.S | re.I)
    if not match:
        raise RuntimeError(f'{domain}: config {config_id} not found in admin')
    return json.loads(html.unescape(match.group(1)))


def save_raw_config(session, domain, config):
    current = session.get(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels', timeout=35)
    current.raise_for_status()
    nonce = re.search(r'name=["\']mgs_cf_nonce["\'][^>]+value=["\']([^"\']+)', current.text, re.I)
    if not nonce:
        raise RuntimeError(f'{domain}: MGS raw-save nonce missing')
    response = session.post(f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels', data={
        'mgs_cf_nonce': html.unescape(nonce.group(1)),
        'mgs_cf_action': 'save_raw',
        'raw_json': json.dumps(config, ensure_ascii=False, indent=2) + '\n',
    }, headers={'Referer': current.url}, timeout=45)
    response.raise_for_status()
    if 'JSON salvo com sucesso' not in response.text:
        raise RuntimeError(f'{domain}: raw config save did not return success for {config.get("id")}')
    saved = raw_config(session, domain, config['id'])
    if saved != config:
        raise RuntimeError(f'{domain}: exact config readback failed for {config.get("id")}')


def save_managers(session, domain, managers):
    url = f'https://{domain}/wp-admin/admin.php?page=mgs-chat-funnels-sms'
    page = session.get(url, timeout=35)
    page.raise_for_status()
    nonce = re.search(r'name=["\']_wpnonce["\'][^>]+value=["\']([^"\']+)', page.text, re.I)
    if not nonce:
        raise RuntimeError(f'{domain}: SMS settings nonce missing')
    data = {
        'action': 'mgs_cf_save_sms',
        '_wpnonce': html.unescape(nonce.group(1)),
        '_wp_http_referer': '/wp-admin/admin.php?page=mgs-chat-funnels-sms',
    }
    for code in sorted(managers):
        data[f'sms_labels[{code}]'] = managers[code]['label']
        data[f'sms_urls[{code}]'] = managers[code]['url']
    response = session.post(f'https://{domain}/wp-admin/admin-post.php', data=data, headers={'Referer': page.url}, timeout=45, allow_redirects=True)
    response.raise_for_status()
    if 'saved=1' not in response.url and 'Configurações SMS salvas.' not in response.text:
        raise RuntimeError(f'{domain}: SMS settings save did not confirm success')
    check = session.get(url, timeout=35)
    check.raise_for_status()
    for code in sorted(managers):
        pattern = rf'name=["\']sms_urls\[{re.escape(code)}\]["\'][^>]+value=["\']([^"\']*)'
        match = re.search(pattern, check.text, re.I)
        if not match or html.unescape(match.group(1)) != managers[code]['url']:
            raise RuntimeError(f'{domain}: private SMS settings readback failed for {code}')


def desired_configs(legacy, domain):
    legacy = copy.deepcopy(legacy)
    if legacy.get('id') != 'CAR-BR-01' or legacy.get('route') != '/chat/car/br1' or legacy.get('mode') != 'cards':
        raise RuntimeError(f'{domain}: unexpected legacy config identity/mode')
    old_offers = legacy.get('offers')
    if not isinstance(old_offers, list) or len(old_offers) != 3:
        raise RuntimeError(f'{domain}: legacy CAR config does not have exactly three offers')
    targets = []
    for offer in old_offers:
        target = offer.get('target') or offer.get('url')
        if not target or (urlparse(target).hostname or '').lower() != domain.lower():
            raise RuntimeError(f'{domain}: missing or cross-domain offer target')
        targets.append(target)
    copy_rows = [
        ('🚗 Financie sem entrada', 'Valores com parcelas', 'R$157,00 a R$299,00'),
        ('💳 Ver ofertas disponíveis', 'Bancos com taxas reduzidas', 'e facilidade para baixo score.'),
        ('🔥 Juros reduzidos 0.98% e sem entrada', 'Consulte se essa condição está disponível para você.', 'Oferta por tempo LIMITADO !'),
    ]
    legacy['offers'] = [
        {'name': name, 'subtitle': subtitle, 'bank': bank, 'image': '', 'logo': '', 'target': target}
        for target, (name, subtitle, bank) in zip(targets, copy_rows)
    ]
    legacy.setdefault('chat', {})['pre_offer_messages'] = ['🔍 Estou pesquisando as melhores condições para você...']
    legacy['chat']['offer_headline'] = '🚗 Encontrei 3 opções que podem combinar com o seu perfil. | Toque na que mais faz sentido para você:'
    legacy['sms_enabled'] = False
    legacy['sms_manager_code'] = ''

    sms = copy.deepcopy(legacy)
    sms['id'] = 'CAR-BR-01-SMS'
    sms['route'] = '/chat-sms/car/br1'
    sms['title'] = 'chat sms cards financiamento de carros'
    sms['sms_enabled'] = True
    sms['sms_manager_code'] = 'G006'
    sms['sms_name_label'] = 'Nome'
    sms['sms_phone_label'] = 'Telefone'
    sms['sms_submit_label'] = 'TRANSFERIR PARA ESPECIALISTA →'
    return legacy, sms


def smoke_hook(main_content, key):
    hook = r'''

// ZEUS_TRANSACTIONAL_SMS_SMOKE_START
add_action('admin_init', static function () {
    if (!isset($_GET['mgs_sms_smoke']) || !hash_equals('__KEY__', (string) $_GET['mgs_sms_smoke']) || !current_user_can('manage_options')) {
        return;
    }
    global $wpdb;
    $table = $wpdb->prefix . 'mgs_chat_leads';
    $before = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
    $mock = static function ($preempt, $args, $url) {
        if (is_string($url) && strpos($url, 'v2.smsfunnel.com.br/integrations/lists/') !== false) {
            return array('headers'=>array(), 'body'=>wp_json_encode(array('success'=>true,'list_id'=>'zeus-transactional-mock')), 'response'=>array('code'=>200,'message'=>'OK'), 'cookies'=>array(), 'filename'=>null);
        }
        return $preempt;
    };
    add_filter('pre_http_request', $mock, 999, 3);
    $request = new WP_REST_Request('POST', '/mgs-chat/v1/lead');
    $request->set_body_params(array('chat_id'=>'CAR-BR-01-SMS','name'=>'Zeus QA Transacional','phone'=>'11999990000','ts'=>((int)round(microtime(true)*1000))-5000,'website'=>'','utm_source'=>'zeusqa','utm_campaign'=>'chat_sms_transactional_smoke'));
    $response = MGS_Chat_SMS::create_lead($request);
    remove_filter('pre_http_request', $mock, 999);
    $data = $response instanceof WP_REST_Response ? $response->get_data() : rest_ensure_response($response)->get_data();
    $lead_id = isset($data['lead_id']) ? (int)$data['lead_id'] : 0;
    $status = $lead_id ? (string)$wpdb->get_var($wpdb->prepare("SELECT sms_funnel_status FROM {$table} WHERE id=%d", $lead_id)) : '';
    $deleted = $lead_id ? $wpdb->delete($table, array('id'=>$lead_id), array('%d')) : false;
    $after = (int)$wpdb->get_var("SELECT COUNT(*) FROM {$table}");
    $ok = !empty($data['ok']) && $status === 'ok:G006' && $deleted === 1 && $before === $after;
    wp_send_json(array('ok'=>$ok,'api_ok'=>!empty($data['ok']),'error'=>(string)($data['error'] ?? ''),'status'=>$status,'row_restored'=>$before===$after,'before'=>$before,'after'=>$after,'mocked_outbound'=>true), $ok ? 200 : 500);
});
// ZEUS_TRANSACTIONAL_SMS_SMOKE_END
'''.replace('__KEY__', key)
    return main_content + hook


def plugin_version(site):
    user = op_field(site['item'], site['api_user'])
    password = op_field(site['item'], site['api_pass'])
    response = requests.get(
        f'https://{site["domain"]}/wp-json/wp/v2/plugins/{MAIN_PLUGIN[:-4]}',
        auth=(user, password), timeout=30,
        headers={'User-Agent': 'MGS-Zeus-Plugin-Version-Readback'},
    )
    response.raise_for_status()
    data = response.json()
    return data.get('version'), data.get('status')


def public_precheck(domain):
    response = requests.get(f'https://{domain}/chat/car/br1/?zeus_before=20260716', timeout=30, headers={'User-Agent': 'MGS-Zeus-Precheck'})
    if response.status_code != 200 or 'const questions =' not in response.text:
        raise RuntimeError(f'{domain}: public legacy route precheck failed')


def main():
    managers = json.load(sys.stdin)
    expected = {f'G{i:03d}' for i in range(1, 7)}
    if set(managers) != expected or any(not managers[k].get('url') for k in expected):
        raise RuntimeError('private SMS catalog input is incomplete')

    final_files = {
        'mgs-chat-funnels/assets/chat-funnels.js': (PLUGIN / 'assets/chat-funnels.js').read_text(),
        'mgs-chat-funnels/assets/chat-funnels.css': (PLUGIN / 'assets/chat-funnels.css').read_text(),
        'mgs-chat-funnels/templates/ciro-index-template.html': (PLUGIN / 'templates/ciro-index-template.html').read_text(),
        MAIN_PLUGIN: (WORK / 'mgs-chat-funnels-bitnami-inline.php').read_text(),
    }
    results = []
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

    selected_domains = {x.strip() for x in os.environ.get('MGS_ROLLOUT_DOMAINS', '').split(',') if x.strip()}
    rollout_sites = [site for site in SITES if not selected_domains or site['domain'] in selected_domains]
    if not rollout_sites:
        raise RuntimeError('no Bitnami rollout sites selected')

    for site in rollout_sites:
        domain = site['domain']
        public_precheck(domain)
        session = login(site)
        site_backup = BACKUP_ROOT / domain
        site_backup.mkdir(parents=True, exist_ok=True)

        before_files = {}
        for file_name in FILES:
            content, _ = editor_page(session, domain, file_name)
            before_files[file_name] = content
            backup_path = site_backup / file_name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(content)
        legacy_before = raw_config(session, domain, 'CAR-BR-01')
        (site_backup / 'car-br-01.json').write_text(json.dumps(legacy_before, ensure_ascii=False, indent=2) + '\n')
        legacy_after, sms_after = desired_configs(legacy_before, domain)

        changed = []
        try:
            for file_name in FILES[:-1]:
                editor_write(session, domain, file_name, final_files[file_name])
                changed.append(file_name)
            editor_write(session, domain, MAIN_PLUGIN, final_files[MAIN_PLUGIN])
            changed.append(MAIN_PLUGIN)

            save_managers(session, domain, managers)
            save_raw_config(session, domain, legacy_after)
            save_raw_config(session, domain, sms_after)

            key = secrets.token_hex(20)
            temp_main = smoke_hook(final_files[MAIN_PLUGIN], key)
            editor_write(session, domain, MAIN_PLUGIN, temp_main)
            try:
                smoke_response = session.get(f'https://{domain}/wp-admin/?mgs_sms_smoke={key}', timeout=45)
                smoke_data = smoke_response.json()
                if smoke_response.status_code != 200 or not smoke_data.get('ok') or not smoke_data.get('mocked_outbound') or not smoke_data.get('row_restored'):
                    safe_smoke = {k: smoke_data.get(k) for k in ('ok','api_ok','error','status','row_restored','before','after','mocked_outbound')}
                    raise RuntimeError(f'{domain}: transactional smoke failed: http={smoke_response.status_code} data={safe_smoke}')
            finally:
                editor_write(session, domain, MAIN_PLUGIN, final_files[MAIN_PLUGIN])

            version, status = plugin_version(site)
            if version != '0.4.1' or status != 'active':
                raise RuntimeError(f'{domain}: plugin version/status readback failed ({version}, {status})')
            final_main, _ = editor_page(session, domain, MAIN_PLUGIN)
            if final_main != final_files[MAIN_PLUGIN] or 'ZEUS_TRANSACTIONAL_SMS_SMOKE' in final_main:
                raise RuntimeError(f'{domain}: final main readback contains drift or temporary smoke code')
            if raw_config(session, domain, 'CAR-BR-01') != legacy_after or raw_config(session, domain, 'CAR-BR-01-SMS') != sms_after:
                raise RuntimeError(f'{domain}: final config readback mismatch')
            results.append({'domain': domain, 'ok': True, 'version': version, 'status': status, 'smoke': smoke_data, 'backup': str(site_backup)})
            print(json.dumps({'domain': domain, 'ok': True, 'version': version, 'smoke': smoke_data, 'backup': str(site_backup)}, ensure_ascii=False), flush=True)
        except Exception:
            # Restore code files that were changed. Configs are retained for forensic recovery;
            # their exact pre-change copy is stored in the backup directory.
            for file_name in reversed(changed):
                try:
                    editor_write(session, domain, file_name, before_files[file_name])
                except Exception:
                    pass
            raise

    manifest = {'backup_root': str(BACKUP_ROOT), 'sites': results}
    (WORK / 'bitnami-rollout-result.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'complete': True, 'backup_root': str(BACKUP_ROOT), 'sites': [x['domain'] for x in results]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
