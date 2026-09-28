#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/yolokfx-direct-quiz-copy-${STAMP}"
MUTATED=0
rollback() {
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo mkdir -p "$BACKUP/failed-state"
    if sudo test -d "$WP/quiz"; then sudo mv "$WP/quiz" "$BACKUP/failed-state/quiz-after-failure"; fi
    if sudo test -d "$BACKUP/quiz-before"; then sudo cp -a "$BACKUP/quiz-before" "$WP/quiz"; fi
    sudo chown -R "$OWNER:$OWNER" "$WP/quiz" 2>/dev/null || true
    sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)){throw new Exception("invalid_backup_json");}update_option("mgs_direct_quiz_landings",$items,false);' --allow-root >/dev/null 2>&1 || true
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

sudo mkdir -p "$BACKUP"
sudo cp -a "$WP/quiz" "$BACKUP/quiz-before"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before.json" >/dev/null
sudo chmod 600 "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-before.json"
sudo python3 - "$BACKUP/landings-before.json" <<'PY'
import json,sys
items=json.load(open(sys.argv[1],encoding='utf-8'))
assert len(items)==18, len(items)
targets=[x for x in items if x.get('country')=='us' and x.get('layout_template') in {'lp1','lp2','lp3'}]
assert len(targets)==18, len(targets)
for layout in ('lp1','lp2','lp3'):
    rows=[x for x in targets if x['layout_template']==layout]
    assert sorted(x['manager_code'] for x in rows)==[f'G{i:03d}' for i in range(1,7)], (layout,rows)
old_title='Get Free SHEIN Products Delivered to Your Home'
old_question='Would you like to get free SHEIN products?'
for x in targets:
    assert x.get('destination_a_url')=='https://yolokfx.com/rec-us-app-shein-circle-of-style/'
    if x['layout_template'] in {'lp1','lp2'}:
        assert x.get('title')==old_title, (x['slug'],x.get('title'))
        assert x.get('question')==old_question, (x['slug'],x.get('question'))
    else:
        assert x.get('title')=='What would you like to receive?', (x['slug'],x.get('title'))
        assert x.get('question')=='Choose a category to continue.', (x['slug'],x.get('question'))
active=[x for x in targets if x.get('active')]
inactive=[x for x in targets if not x.get('active')]
assert len(active)==17
assert [(x['layout_template'],x['manager_code'],x['slug']) for x in inactive]==[('lp1','G004','sh1-g004')]
print(json.dumps({'preflight':'PASS','items':len(items),'targets':len(targets),'active':len(active),'inactive':[x['slug'] for x in inactive]},separators=(',',':')))
PY

MUTATED=1
change_json=$(sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();
$oldTitle="Get Free SHEIN Products Delivered to Your Home";
$oldQuestion="Would you like to get free SHEIN products?";
$newTitle="Get Free Products Delivered to Your Home";
$newQuestion="Would you like to get free products?";
$v3OldTitle="What would you like to receive?";
$changedItems=0;$changedFields=0;$counts=["lp1"=>0,"lp2"=>0,"lp3"=>0];
foreach($items as &$item){
 $layout=(string)($item["layout_template"]??"");
 if(($item["country"]??"")!=="us"||!in_array($layout,["lp1","lp2","lp3"],true)){continue;}
 if($layout==="lp1"||$layout==="lp2"){
  if(($item["title"]??"")!==$oldTitle||($item["question"]??"")!==$oldQuestion){throw new Exception("precondition_drift_".($item["slug"]??"unknown"));}
  $item["title"]=$newTitle;$item["question"]=$newQuestion;$changedFields+=2;
 } else {
  if(($item["title"]??"")!==$v3OldTitle){throw new Exception("precondition_drift_".($item["slug"]??"unknown"));}
  $item["title"]=$newTitle;$changedFields+=1;
 }
 $changedItems++;$counts[$layout]++;
}
unset($item);
if($changedItems!==18||$changedFields!==30||$counts!==["lp1"=>6,"lp2"=>6,"lp3"=>6]){throw new Exception("target_count_mismatch");}
if(!MGS_Direct_Quiz::save_items($items)){throw new Exception("option_save_failed");}
$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}
if(count($sync)!==17){throw new Exception("sync_count_".count($sync));}
echo wp_json_encode(["changed_items"=>$changedItems,"changed_fields"=>$changedFields,"counts"=>$counts,"active_sync_count"=>count($sync)],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)

sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-after.json" >/dev/null
sudo chmod 600 "$BACKUP/landings-after.json"
sudo python3 - "$BACKUP/landings-before.json" "$BACKUP/landings-after.json" "$WP" <<'PY'
import copy,hashlib,json,os,sys
before=json.load(open(sys.argv[1],encoding='utf-8'))
after=json.load(open(sys.argv[2],encoding='utf-8'))
wp=sys.argv[3]
assert len(before)==len(after)==18
b={str(x['id']):x for x in before}; a={str(x['id']):x for x in after}
assert set(b)==set(a)
new_title='Get Free Products Delivered to Your Home'
new_question='Would you like to get free products?'
old_title='Get Free SHEIN Products Delivered to Your Home'
old_question='Would you like to get free SHEIN products?'
old_v3='What would you like to receive?'
changes=[]; active=[]
for ident,old in b.items():
    cur=a[ident]
    layout=old.get('layout_template')
    assert old.get('country')=='us' and layout in {'lp1','lp2','lp3'}
    old_cmp=copy.deepcopy(old); cur_cmp=copy.deepcopy(cur)
    if layout in {'lp1','lp2'}:
        assert old_cmp.pop('title')==old_title and old_cmp.pop('question')==old_question
        assert cur_cmp.pop('title')==new_title and cur_cmp.pop('question')==new_question
        fields=['title','question']
    else:
        assert old_cmp.pop('title')==old_v3
        assert cur_cmp.pop('title')==new_title
        fields=['title']
    assert old_cmp==cur_cmp, (cur.get('slug'),'non_target_drift')
    changes.append({'slug':cur['slug'],'layout':layout,'fields':fields,'active':int(bool(cur.get('active')))})
    if cur.get('active'): active.append(cur)
assert len(changes)==18 and len(active)==17
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
        assert 'Choose a category to continue.' not in html
        assert html.count('data-mgs-dq-cta')==7
        assert html.count('class="mgs-dq-category"')==6
inactive=os.path.join(wp,'quiz','us','sh1-g004','index.html')
assert not os.path.exists(inactive)
summary={'readback':'PASS','items':len(after),'changed_items':len(changes),'active_routes':len(active),'inactive_route':'sh1-g004','all_non_target_fields_preserved':True,'static_files_validated':len(active),'changes':changes}
open(os.path.join(os.path.dirname(sys.argv[2]),'verification.json'),'w',encoding='utf-8').write(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='changes'},separators=(',',':')))
PY
sudo python3 - "$BACKUP" <<'PY'
import hashlib,json,os,sys
root=sys.argv[1]
files=[]
for cur,dirs,names in os.walk(root):
    dirs.sort(); names.sort()
    for name in names:
        p=os.path.join(cur,name)
        if os.path.isfile(p):
            h=hashlib.sha256(open(p,'rb').read()).hexdigest()
            files.append({'path':os.path.relpath(p,root),'sha256':h,'bytes':os.path.getsize(p)})
with open(os.path.join(root,'SHA256-MANIFEST.json'),'w',encoding='utf-8') as f:
    json.dump({'files':files},f,separators=(',',':'))
    f.write('\n')
print(json.dumps({'backup_files':len(files),'manifest':os.path.join(root,'SHA256-MANIFEST.json')},separators=(',',':')))
PY
sudo test -d "$BACKUP/quiz-before"
sudo test -s "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-after.json"
sudo test -s "$BACKUP/verification.json"
sudo test -s "$BACKUP/SHA256-MANIFEST.json"
MUTATED=0
printf 'SITE=yolokfx.com\nVERSION=%s\nSTATUS=%s\nBACKUP=%s\nCHANGE=%s\n' "$version" "$status" "$BACKUP" "$change_json"
