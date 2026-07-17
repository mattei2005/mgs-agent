<?php
if (!defined('ABSPATH')) exit(1);
echo wp_json_encode(array(
    'tz' => MGS_Chat_SMS::BUSINESS_TIMEZONE,
    'start' => MGS_Chat_SMS::local_date_bound_to_utc('2026-07-15'),
    'end' => MGS_Chat_SMS::local_date_bound_to_utc('2026-07-15', true),
    'display' => MGS_Chat_SMS::format_created_at('2026-07-15 03:00:00'),
), JSON_UNESCAPED_SLASHES) . PHP_EOL;
