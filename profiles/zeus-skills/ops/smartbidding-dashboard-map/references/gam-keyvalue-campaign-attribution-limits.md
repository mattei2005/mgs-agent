# GAM Key Values and campaign-attribution limits

Read-only discovery validated on Eggbev1–9 September2026, request1547601740734664766. Evidence: `/root/mgs-agent/work/eggbev-campaign-1547601740734664766/`.

## Actual dashboard contract

- `/reports/gam-key-values` deliberately makes no report request until KeyValue is selected. A blank table says `Select a KeyValue to load the report`; this is not proof of no data.
- Open `Select a key`, choose exact `utm_campaign`. Observed `POST https://api.jbfdigital.com.br/report/gam_custom_criteria` with `initialDate`, `finalDate`, `publishers`, `currency`, `custom_criteria_key: "utm_campaign"`. Successful read returned201. Set explicit currency and exact publisher from validated scope.
- Other visible choices: `jbf_operation`, `placement`, `utm_adgroup`, `utm_content`, `utm_medium`, `utm_source`.
- Returned fields include `PK_GAM_CUSTOM_CRITERIA`, ISO `DATE`, `PUBLISHER`, `CUSTOM_CRITERIA_KEY`, `CUSTOM_CRITERIA_VALUE`, `SLOT_ID`, `COMPANY`, `DOMAIN`, metrics and `REVENUE`. The observed utm_campaign response did NOT contain URL or vertical on the same row.
- Changing the chosen custom-criteria key produces a different marginal report; it is not proof of a joint distribution of campaign and operation/vertical.

## Attribution safety

Do not join a campaign-only report to a vertical/URL-only report merely by domain/date or shared slot. Require a unique joint identity. In this fixture every one of18 ad slots serving EMP also served CC; no returned `(date, slot)` campaign record had EMP as its sole matched product. Assigning all revenue/campaigns on those slots to EMP would misclassify CC.

AdGroup's vertical can describe the campaign/account, while Operation identifies a landing-page product. Campaign names are not financial lineage. The Eggbev campaigns containing Loan yielded zero AdGroup revenue; tokens included `pg_22340`, `pg_22411`, `pg_22412`, and literal `teste dup`. They do not explain the EMP revenue and are not validated EMP assignments.

## Verified fixture (do not generalize totals)

- Vertical snapshot EMP CAD28.32 gross: mct19.06, facebook with medium d7.72, direct1.49, facebook with blank medium0.05. SOURCE direct is a SB source field, not proof of a g00X-s tag.
- Operation/URL previously confirmed loan URLs, but its rows do not expose utm_campaign.
- Queried same publisher/date range/CAD: AdGroup1757 rows; Messenger1043 rows; Messenger Messages9490 rows; GAM KeyValues/utm_campaign2505 rows. AdGroup/Message/GAM primary keys unique; dates/domain checked. These totals are query results, not a claim of joint historical attribution.
- AdGroup entries are CC/blank; Messenger and Message use CC/RE/blank rather than EMP. KeyValues contains campaign values, but mixed CC/EMP slots prevent safe attribution of the EMP financial subset.
- Outcome: channel and some destination URLs identified, but no exact utm_campaign→EMP revenue bridge established from these consulted reports. This is not a claim that SB has no other possible data source. The required next evidence is historical data with date + campaign + URL/vertical jointly present (e.g. an appropriate authorized report/export), followed by reconciliation to original GAM. Do not subtract SB28.32 from GAM or invent a split.
