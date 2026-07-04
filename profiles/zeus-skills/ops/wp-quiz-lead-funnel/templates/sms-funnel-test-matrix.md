# SMS Funnel Test Matrix Template

Use this after configuring or diagnosing quiz variants.

## Direct Backend Test

| Quiz | Slug | Expected gestor | WP response | SMS status | Expected list_id | Result |
|---|---|---:|---|---|---|---|
| G001 | `/quiz-car-parcelas-g001/` | G001 |  |  |  |  |
| G002 | `/quiz-car-parcelas/` | G002 |  |  |  |  |
| G003 | `/quiz-car-parcelas-g003/` | G003 |  |  |  |  |
| G004 | `/quiz-car-parcelas-g004/` | G004 |  |  |  |  |
| G005 | `/quiz-car-parcelas-g005/` | G005 |  |  |  |  |
| G006 | `/quiz-car-parcelas-g006/` | G006 |  |  |  |  |

## Browser Frontend Test

For each quiz:

1. Open public URL with test UTMs.
2. Click an option.
3. Fill name and unique phone.
4. Submit with the visible button.
5. Confirm success/redirect.
6. Query WP DB for name/phone/campaign.
7. Confirm `sms_funnel_status = ok:G00X`.
8. Confirm stored SMS response has expected `list_id`.

## Final Verdict

- Backend OK + Browser OK + correct list_id = WordPress side healthy.
- Backend OK + Browser fail = frontend/JS/form/timestamp issue.
- Backend fail + Browser fail = routing/config/SMS Funnel endpoint issue.
- WordPress OK but SMS dashboard empty = likely SMS dashboard delay/cache/filter/deduplication.
