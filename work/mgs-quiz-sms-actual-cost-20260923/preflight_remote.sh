#!/usr/bin/env bash
set -euo pipefail
WP=(sudo -u runcloud2 wp --path=/home/runcloud2/webapps/creditoparaveiculo --skip-themes)
printf 'HOME='
"${WP[@]}" option get home
"${WP[@]}" plugin get mgs-quiz-carro --fields=name,status,version --format=json
printf 'QUIZ_DB_STATE\n'
"${WP[@]}" eval 'global $wpdb; $tables=$wpdb->get_col("SHOW TABLES"); $tables=array_values(array_filter($tables,function($t){return strpos($t,"mgs_quiz")!==false;})); foreach($tables as $t){echo $t,"\n";} $rt=$wpdb->prefix."mgs_quiz_sms_revenue"; echo "REVENUE_COLUMNS\n"; echo wp_json_encode($wpdb->get_results("DESCRIBE {$rt}",ARRAY_A),JSON_UNESCAPED_SLASHES),"\n";'
