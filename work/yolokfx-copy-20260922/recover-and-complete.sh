#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
ORIGINAL_BACKUP=/home/runcloud/backups/yolokfx-direct-quiz-copy-20260923T022709Z
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/yolokfx-direct-quiz-copy-recovery-${STAMP}"
MUTATED=0
rollback() {
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo mkdir -p "$BACKUP/failed-state"
    if sudo test -d "$WP/quiz"; then sudo mv "$WP/quiz" "$BACKUP/failed-state/quiz-after-recovery-failure"; fi
    if sudo test -d "$ORIGINAL_BACKUP/quiz-before"; then sudo cp -a "$ORIGINAL_BACKUP/quiz-before" "$WP/quiz"; fi
    sudo chown -R "$OWNER:$OWNER" "$WP/quiz" 2>/dev/null || true
    sudo chown "$OWNER:$OWNER" "$ORIGINAL_BACKUP/landings-before.json" 2>/dev/null || true
    sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$ORIGINAL_BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)){throw new Exception("invalid_backup_json");}update_option("mgs_direct_quiz_landings",$items,false);$rb=get_option("mgs_direct_quiz_landings",[]);if(wp_json_encode($rb)!==wp_json_encode($items)){throw new Exception("rollback_option_readback_failed");}echo "ROLLBACK_OPTION_OK";' --allow-root >&2 || true
  fi
  printf 'ROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR

home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$home" == 'https://yolokfx.com' ]]
[[ "$version" == '1.2.0' && "$status" == 'active' ]]
sudo test -s "$ORIGINAL_BACKUP/landings-before.json"
sudo test -s "$ORIGINAL_BACKUP/landings-after.json"
sudo test -d "$ORIGINAL_BACKUP/quiz-before"
sudo test -d "$ORIGINAL_BACKUP/failed-state/quiz-after-failure"

sudo mkdir -p "$BACKUP"
sudo cp -a "$WP/quiz" "$BACKUP/quiz-before-recovery"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before-recovery.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-before-recovery.json" "$ORIGINAL_BACKUP/landings-before.json"
sudo chmod 600 "$BACKUP/landings-before-recovery.json" "$ORIGINAL_BACKUP/landings-before.json"
sudo python3 - "$ORIGINAL_BACKUP/landings-before.json" "$BACKUP/landings-before-recovery.json" "$WP" <<'PY'
import copy,json,os,sys
old=json.load(open(sys.argv[1],encoding='utf-8'))
cur=json.load(open(sys.argv[2],encoding='utf-8'))
wp=sys.argv[3]
assert len(old)==len(cur)==18
oldmap={str(x['id']):x for x in old}; curmap={str(x['id']):x for x in cur}
assert set(oldmap)==set(curmap)
new_title='Get Free Products Delivered to Your Home'
new_question='Would you like to get free products?'
for ident,b in oldmap.items():
    a=curmap[ident]; layout=b.get('layout_template')
    bc=copy.deepcopy(b); ac=copy.deepcopy(a)
    if layout in {'lp1','lp2'}:
        assert bc.pop('title')=='Get Free SHEIN Products Delivered to Your Home'
        assert bc.pop('question')=='Would you like to get free SHEIN products?'
        assert ac.pop('title')==new_title
        assert ac.pop('question')==new_question
    elif layout=='lp3':
        assert bc.pop('title')=='What would you like to receive?'
        assert ac.pop('title')==new_title
    else:
        raise AssertionError(layout)
    assert bc==ac, (a.get('slug'),'non_target_drift')
active=[x for x in cur if x.get('active')]
assert len(active)==17
for x in active:
    html=open(os.path.join(wp,'quiz','us',x['slug'],'index.html'),encoding='utf-8').read()
    assert new_title not in html
    if x['layout_template'] in {'lp1','lp2'}:
        assert 'Get Free SHEIN Products Delivered to Your Home' in html
        assert 'Would you like to get free SHEIN products?' in html
    else:
        assert 'What would you like to receive?' in html
print(json.dumps({'partial_state_confirmed':True,'option_new':18,'static_old':17,'non_target_fields_preserved':True},separators=(',',':')))
PY

MUTATED=1
sync_json=$(sudo -u "$OWNER" wp --path="$WP" eval '$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}if(count($sync)!==17){throw new Exception("sync_count_".count($sync));}echo wp_json_encode(["active_sync_count"=>count($sync)],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);' --allow-root)
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-after-recovery.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-after-recovery.json"
sudo chmod 600 "$BACKUP/landings-after-recovery.json"
sudo python3 - "$BACKUP/landings-before-recovery.json" "$BACKUP/landings-after-recovery.json" "$WP" "$BACKUP/verification.json" <<'PY'
import hashlib,json,os,sys
before=json.load(open(sys.argv[1],encoding='utf-8'))
after=json.load(open(sys.argv[2],encoding='utf-8'))
wp,out_path=sys.argv[3:]
assert before==after
new_title='Get Free Products Delivered to Your Home'
new_question='Would you like to get free products?'
old_title='Get Free SHEIN Products Delivered to Your Home'
old_question='Would you like to get free SHEIN products?'
old_v3='What would you like to receive?'
active=[x for x in after if x.get('active')]
assert len(active)==17
rows=[]
for x in active:
    path=os.path.join(wp,'quiz','us',x['slug'],'index.html')
    assert os.path.isfile(path), path
    html=open(path,encoding='utf-8').read()
    assert 'MGS Direct Quiz static; plugin=1.2.0' in html
    assert new_title in html
    assert old_title not in html and old_question not in html and old_v3 not in html
    assert '<form' not in html.lower() and '<input' not in html.lower()
    assert 'src="http://' not in html and 'href="http://' not in html
    if x['layout_template'] in {'lp1','lp2'}:
        assert new_question in html
        assert html.count('data-mgs-dq-cta')==2
    else:
        assert html.count('data-mgs-dq-cta')==7
        assert html.count('class="mgs-dq-category"')==6
    rows.append({'slug':x['slug'],'layout':x['layout_template'],'sha256':hashlib.sha256(html.encode()).hexdigest()})
assert not os.path.exists(os.path.join(wp,'quiz','us','sh1-g004','index.html'))
summary={'recovery':'PASS','option_unchanged_during_recovery':True,'active_static_routes':len(rows),'inactive_route':'sh1-g004','all_requested_copy_present':True,'all_old_visible_copy_absent_from_active_static':True,'routes':rows}
open(out_path,'w',encoding='utf-8').write(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='routes'},separators=(',',':')))
PY
sudo chown "$OWNER:$OWNER" "$BACKUP/verification.json"
sudo python3 - "$BACKUP" <<'PY'
import hashlib,json,os,sys
root=sys.argv[1]
files=[]
for cur,dirs,names in os.walk(root):
    dirs.sort(); names.sort()
    for name in names:
        p=os.path.join(cur,name)
        if os.path.isfile(p):
            files.append({'path':os.path.relpath(p,root),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'bytes':os.path.getsize(p)})
with open(os.path.join(root,'SHA256-MANIFEST.json'),'w',encoding='utf-8') as f:
    json.dump({'files':files},f,separators=(',',':')); f.write('\n')
print(json.dumps({'backup_files':len(files),'manifest':os.path.join(root,'SHA256-MANIFEST.json')},separators=(',',':')))
PY
sudo test -d "$BACKUP/quiz-before-recovery"
sudo test -s "$BACKUP/landings-before-recovery.json"
sudo test -s "$BACKUP/landings-after-recovery.json"
sudo test -s "$BACKUP/verification.json"
sudo test -s "$BACKUP/SHA256-MANIFEST.json"
MUTATED=0
printf 'SITE=yolokfx.com\nVERSION=%s\nSTATUS=%s\nBACKUP=%s\nORIGINAL_BACKUP=%s\nSYNC=%s\n' "$version" "$status" "$BACKUP" "$ORIGINAL_BACKUP" "$sync_json"
