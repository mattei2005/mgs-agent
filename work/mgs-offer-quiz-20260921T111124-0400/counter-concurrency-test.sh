#!/usr/bin/env bash
set -euo pipefail
webroot=/home/runcloud/webapps/dicasfinancas
fixture=/tmp/mgs-counter-concurrency-fixture.php
prefix=/tmp/mgs-counter-result-
cleanup(){ rm -f "$fixture" ${prefix}*.json; }
trap cleanup EXIT

sudo -u runcloud wp --path="$webroot" eval 'global $wpdb; $table=$wpdb->prefix."mgs_offer_quiz_daily_views"; $wpdb->delete($table,array("view_date"=>"2099-12-31"),array("%s"));' --allow-root
seq 1 20 | xargs -P 10 -I{} sh -c 'sudo -u runcloud wp --path="/home/runcloud/webapps/dicasfinancas" eval-file /tmp/mgs-counter-concurrency-fixture.php --allow-root > "/tmp/mgs-counter-result-{}.json"'

sorted=$(python3 -c 'import glob,json; values=sorted(json.load(open(path,encoding="utf-8"))["views_today"] for path in glob.glob("/tmp/mgs-counter-result-*.json")); print(" ".join(map(str,values))+" ",end="")')
expected=$(seq 1 20 | tr '\n' ' ')
[[ "$sorted" == "$expected" ]]

row=$(sudo -u runcloud wp --path="$webroot" eval 'global $wpdb; $table=$wpdb->prefix."mgs_offer_quiz_daily_views"; $count=(int)$wpdb->get_var($wpdb->prepare("SELECT view_count FROM {$table} WHERE view_date=%s","2099-12-31")); echo wp_json_encode(array("view_count"=>$count,"display_count"=>MGS_Offer_Quiz::COUNTER_BASELINE+$count-1))."\n";' --allow-root)
[[ "$row" == '{"view_count":20,"display_count":1911}' ]]

remaining=$(sudo -u runcloud wp --path="$webroot" eval 'global $wpdb; $table=$wpdb->prefix."mgs_offer_quiz_daily_views"; $wpdb->delete($table,array("view_date"=>"2099-12-31"),array("%s")); $remaining=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE view_date=%s","2099-12-31")); echo "remaining={$remaining}\n";' --allow-root)
[[ "$remaining" == 'remaining=0' ]]

echo "concurrency_results=$sorted"
echo "fixture_row=$row"
echo "fixture_cleanup=ok"
