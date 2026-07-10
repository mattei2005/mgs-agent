## Inventário mínimo

Todo pipeline de classificação/renomeação deve manter inventário com pelo menos:

```text
filename
proposed_filename
vertical
country
language
format
angle
person
orientation
p_orient
variant
status
performance_label
source
source_manager
page_id
asset_drive_id
meta_creative_id
origin_campaign_id
width
height
aspect_ratio
placement_fit
checksum_md5
clean_metadata_status
created_at
notes
```

Valores usuais:

```text
person: PERSON, NO_PERSON, UNKNOWN
orientation: VERTICAL, HORIZONTAL, REVIEW
status: READY, TESTING, TESTED, WINNER, REJECTED, LEGACY, REVIEW
performance_label: GOOD, BAD, INCONCLUSIVE, UNKNOWN
```
