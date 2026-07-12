#!/usr/bin/env python3
from pathlib import Path

root = Path('/root/mgs-agent/work/mgs-quiz-calendar-173/mgs-quiz-carro')
admin = (root / 'includes/class-mgs-quiz-admin.php').read_text(encoding='utf-8')
bootstrap = (root / 'mgs-quiz-carro.php').read_text(encoding='utf-8')

checks = {
    'version_173_header': 'Version:     1.7.3' in bootstrap,
    'version_173_constant': "MGS_QUIZ_VERSION', '1.7.3'" in bootstrap,
    'range_trigger': 'id="mgsqDateRangeTrigger"' in admin,
    'hidden_from': 'type="hidden" name="from" id="mgsqDateFrom"' in admin,
    'hidden_to': 'type="hidden" name="to" id="mgsqDateTo"' in admin,
    'two_calendars': 'data-calendar-index="0"' in admin and 'data-calendar-index="1"' in admin,
    'yesterday_preset': 'data-preset="yesterday"' in admin,
    'last_7_preset': 'data-preset="last7"' in admin,
    'last_30_preset': 'data-preset="last30"' in admin,
    'this_month_preset': 'data-preset="thisMonth"' in admin,
    'last_month_preset': 'data-preset="lastMonth"' in admin,
    'custom_preset': 'data-preset="custom"' in admin,
    'cancel_apply': 'id="mgsqDateCancel"' in admin and 'id="mgsqDateApply"' in admin,
    'date_range_logic': 'function selectDate(' in admin and 'function applyDraft(' in admin,
    'mobile_one_month': '@media(max-width:782px)' in admin and '.mgsq-calendar-panel:nth-child(2){display:none}' in admin,
    'default_yesterday_preserved': "modify( '-1 day' )->format( 'Y-m-d' )" in admin,
    'no_compare_to': 'Compare to:' not in admin and 'Compare To:' not in admin,
    'no_730_limit': '730 day' not in admin,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('CALENDAR_UI_TEST_FAIL ' + ','.join(failed))
print('CALENDAR_UI_TEST_OK checks=' + str(len(checks)))
