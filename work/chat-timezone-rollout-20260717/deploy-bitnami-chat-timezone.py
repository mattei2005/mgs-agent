#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/chat-timezone-rollout-20260717'
BASE_MODULE = ROOT / 'work/chat-sms-rollout-20260716/bitnami-rollout.py'
FINAL_PATH = WORK / 'mgs-chat-funnels-bitnami-inline.php'
EXPECTED_OLD_SHA = 'b79e64292604d04178f7785cbf24c39c03b94032236e352e10fc1811553ab775'
EXPECTED_NEW_SHA = '17115575ded0fa48d977cabd3649c7628fc4a720db88bca6ab010ea7e9a55c1e'
MANAGERS = {'openzed.com': 'G003', 'cliquet.com': 'G002'}
BACKUP_ROOT = Path('/root/mgs-agent-backups/chat-timezone-rollout') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

spec = importlib.util.spec_from_file_location('bitnami_base', BASE_MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError('could not load Bitnami rollout helper')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def smoke_hook(main_content, key, expected_manager):
    hook = r'''

// ZEUS_TIMEZONE_SMS_SMOKE_START
add_action('admin_init', static function () {
    if (!isset($_GET['mgs_timezone_smoke']) || !hash_equals('__KEY__', (string) $_GET['mgs_timezone_smoke']) || !current_user_can('manage_options')) return;
    global $wpdb;
    $table = $wpdb->prefix . 'mgs_chat_leads';
    $before = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
    $mock = static function ($preempt, $args, $url) {
        if (is_string($url) && strpos($url, 'v2.smsfunnel.com.br/integrations/lists/') !== false) {
            return array('headers'=>array(), 'body'=>wp_json_encode(array('success'=>true,'list_id'=>'zeus-timezone-mock')), 'response'=>array('code'=>200,'message'=>'OK'), 'cookies'=>array(), 'filename'=>null);
        }
        return $preempt;
    };
    add_filter('pre_http_request', $mock, 999, 3);
    $request = new WP_REST_Request('POST', '/mgs-chat/v1/lead');
    $request->set_body_params(array('chat_id'=>'CAR-BR-01-SMS','name'=>'Zeus QA Timezone','phone'=>'11999990000','ts'=>((int)round(microtime(true)*1000))-5000,'website'=>'','utm_source'=>'zeusqa','utm_campaign'=>'chat_timezone_smoke'));
    $response = MGS_Chat_SMS::create_lead($request);
    remove_filter('pre_http_request', $mock, 999);
    $data = $response instanceof WP_REST_Response ? $response->get_data() : rest_ensure_response($response)->get_data();
    $lead_id = isset($data['lead_id']) ? (int)$data['lead_id'] : 0;
    $status = $lead_id ? (string)$wpdb->get_var($wpdb->prepare("SELECT sms_funnel_status FROM {$table} WHERE id=%d", $lead_id)) : '';
    $deleted = $lead_id ? $wpdb->delete($table, array('id'=>$lead_id), array('%d')) : false;
    $after = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
    $start = MGS_Chat_SMS::local_date_bound_to_utc('2026-07-15');
    $end = MGS_Chat_SMS::local_date_bound_to_utc('2026-07-15', true);
    $display = MGS_Chat_SMS::format_created_at('2026-07-15 03:00:00');
    $ok = !empty($data['ok']) && $status === 'ok:__MANAGER__' && $deleted === 1 && $before === $after && $start === '2026-07-15 03:00:00' && $end === '2026-07-16 03:00:00' && $display === '15/07/2026, 00:00';
    wp_send_json(array('ok'=>$ok,'api_ok'=>!empty($data['ok']),'error'=>(string)($data['error'] ?? ''),'lead_id'=>$lead_id,'status'=>$status,'row_restored'=>$before===$after,'before'=>$before,'after'=>$after,'mocked_outbound'=>true,'timezone'=>MGS_Chat_SMS::BUSINESS_TIMEZONE,'start'=>$start,'end_exclusive'=>$end,'display'=>$display), $ok ? 200 : 500);
});
// ZEUS_TIMEZONE_SMS_SMOKE_END
'''.replace('__KEY__', key).replace('__MANAGER__', expected_manager)
    return main_content + hook


def public_check(domain):
    for route, marker in (('/chat/car/br1/', 'const questions ='), ('/chat-sms/car/br1/', 'mgs-cf-sms-form')):
        r = requests.get(f'https://{domain}{route}?zeus_tz=20260717', timeout=35, headers={'User-Agent':'MGS-Zeus-Timezone-Rollout'})
        if r.status_code != 200 or marker not in r.text:
            raise RuntimeError(f'{domain}: public check failed route={route} http={r.status_code}')


def main():
    target = os.environ.get('MGS_ROLLOUT_DOMAINS', '').strip()
    selected = [s for s in base.SITES if not target or s['domain'] in {x.strip() for x in target.split(',')}]
    if not selected:
        raise RuntimeError('no Bitnami sites selected')
    final_main = FINAL_PATH.read_text()
    if hashlib.sha256(final_main.encode()).hexdigest() != EXPECTED_NEW_SHA:
        raise RuntimeError('local final inline hash mismatch')
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for site in selected:
        domain = site['domain']
        manager = MANAGERS[domain]
        public_check(domain)
        session = base.login(site)
        before, _ = base.editor_page(session, domain, base.MAIN_PLUGIN)
        before_sha = hashlib.sha256(before.encode()).hexdigest()
        if before_sha != EXPECTED_OLD_SHA:
            raise RuntimeError(f'{domain}: preflight hash mismatch {before_sha}')
        version, status = base.plugin_version(site)
        if version != '0.4.1' or status != 'active':
            raise RuntimeError(f'{domain}: unexpected preflight version/status {version}/{status}')
        backup_dir = BACKUP_ROOT / domain
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / 'mgs-chat-funnels.php'
        backup_file.write_text(before)
        backup_file.chmod(0o600)
        changed = False
        try:
            base.editor_write(session, domain, base.MAIN_PLUGIN, final_main)
            changed = True
            key = secrets.token_hex(20)
            temp = smoke_hook(final_main, key, manager)
            base.editor_write(session, domain, base.MAIN_PLUGIN, temp)
            try:
                r = session.get(f'https://{domain}/wp-admin/?mgs_timezone_smoke={key}', timeout=45)
                data = r.json()
                if r.status_code != 200 or not data.get('ok') or not data.get('mocked_outbound') or not data.get('row_restored'):
                    raise RuntimeError(f'{domain}: smoke failed http={r.status_code} data={data}')
            finally:
                base.editor_write(session, domain, base.MAIN_PLUGIN, final_main)
            final_readback, _ = base.editor_page(session, domain, base.MAIN_PLUGIN)
            final_sha = hashlib.sha256(final_readback.encode()).hexdigest()
            if final_sha != EXPECTED_NEW_SHA or 'ZEUS_TIMEZONE_SMS_SMOKE' in final_readback:
                raise RuntimeError(f'{domain}: final readback mismatch {final_sha}')
            version, status = base.plugin_version(site)
            if version != '0.4.2' or status != 'active':
                raise RuntimeError(f'{domain}: final version/status mismatch {version}/{status}')
            public_check(domain)
            safe = {k:data.get(k) for k in ('ok','status','row_restored','before','after','mocked_outbound','timezone','start','end_exclusive','display')}
            result = {'domain':domain,'ok':True,'version':version,'status':status,'manager':manager,'sha256':final_sha,'backup':str(backup_file),'smoke':safe}
            results.append(result)
            print(json.dumps(result,ensure_ascii=False),flush=True)
        except Exception:
            if changed:
                try:
                    base.editor_write(session, domain, base.MAIN_PLUGIN, before)
                except Exception:
                    pass
            raise
    manifest={'backup_root':str(BACKUP_ROOT),'sites':results}
    (WORK/'bitnami-timezone-rollout-result.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'complete':True,'sites':[x['domain'] for x in results],'backup_root':str(BACKUP_ROOT)},ensure_ascii=False))


if __name__ == '__main__':
    main()
