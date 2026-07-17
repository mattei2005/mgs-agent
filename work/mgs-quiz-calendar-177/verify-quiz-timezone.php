<?php
if (!defined('ABSPATH')) exit(1);
global $wpdb;
$start = MGS_Quiz_Admin::local_date_bound_to_utc('2026-07-15');
$end = MGS_Quiz_Admin::local_date_bound_to_utc('2026-07-15', true);
$table = $wpdb->prefix . 'mgs_quiz_leads';
$count = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE created_at >= %s AND created_at < %s", $start, $end));
echo wp_json_encode(array(
    'tz' => MGS_Quiz_Admin::BUSINESS_TIMEZONE,
    'start' => $start,
    'end' => $end,
    'display' => MGS_Quiz_Admin::format_created_at('2026-07-15 03:00:00'),
    'count' => $count,
), JSON_UNESCAPED_SLASHES) . PHP_EOL;
