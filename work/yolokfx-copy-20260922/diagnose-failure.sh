#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
BACK=/home/runcloud/backups/yolokfx-direct-quiz-copy-20260923T022709Z
sudo python3 - "$BACK/landings-before.json" "$BACK/landings-after.json" "$WP/quiz/us/sh3-g002/index.html" "$WP/quiz/us/sh1-g002/index.html" <<'PY'
import json,sys,os
before=json.load(open(sys.argv[1],encoding='utf-8'))
after=json.load(open(sys.argv[2],encoding='utf-8'))
def sample(items,slug):
 x=next(y for y in items if y.get('slug')==slug)
 return {'slug':slug,'title':x.get('title'),'question':x.get('question')}
out={'backup_before':sample(before,'sh1-g002'),'backup_after':sample(after,'sh1-g002'),'backup_before_v3':sample(before,'sh3-g002'),'backup_after_v3':sample(after,'sh3-g002')}
for label,path in [('static_v3',sys.argv[3]),('static_v1',sys.argv[4])]:
 html=open(path,encoding='utf-8').read()
 out[label]={
  'new_title': 'Get Free Products Delivered to Your Home' in html,
  'old_v12_title': 'Get Free SHEIN Products Delivered to Your Home' in html,
  'new_question': 'Would you like to get free products?' in html,
  'old_question': 'Would you like to get free SHEIN products?' in html,
  'v3_old_title': 'What would you like to receive?' in html,
  'v3_question_present': 'Choose a category to continue.' in html,
 }
print(json.dumps(out,ensure_ascii=False,separators=(',',':')))
PY
sudo -u runcloud env MGS_DQ_BACKUP_JSON="$BACK/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);echo wp_json_encode(["decode_ok"=>is_array($items),"count"=>is_array($items)?count($items):null,"first_title"=>is_array($items)?($items[0]["title"]??null):null],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);' --allow-root
