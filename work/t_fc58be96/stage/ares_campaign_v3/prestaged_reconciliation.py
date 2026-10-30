"""Slot-safe recovery of prestaged copies; never use lineage alone twice."""
from __future__ import annotations
import copy

def copy_parameters(payload, operation):
    # Validate-only acceptance is not evidence for changing the CTA subtype.
    return copy.deepcopy(payload)

def resolve_slot(rows, ad, adset_id, record, ci, ai, lineage_count):
    names={f'ad_copy_{ci}_{ai}',f'recovery_ad_copy_{ci}_{ai}'}
    persisted=[]
    for entry in record.get('write_journal',[]):
        for item in entry.get('confirmed',[]):
            ident=(item.get('ids') or {}).get('copied_ad_id')
            if item.get('name') in names and ident and str(ident) not in persisted:
                persisted.append(str(ident))
    for name in sorted(names):
        ident=(record.get('confirmed_objects',{}).get(name) or {}).get('copied_ad_id')
        if ident and str(ident) not in persisted:persisted.append(str(ident))
    live={str(row.get('id')):row for row in rows if row.get('status') not in {'DELETED','ARCHIVED'}}
    for ident in persisted:
        if ident in live and (str(live[ident].get('adset_id'))!=str(adset_id) or str(live[ident].get('source_ad_id'))!=str(ad.source_ad_id)):
            raise ValueError('persisted prestaged slot parent/lineage mismatch')
    wanted=ad.creative_payload.get('name') or ''
    matches=[]
    for row in live.values():
        if str(row.get('adset_id'))!=str(adset_id) or str(row.get('source_ad_id'))!=str(ad.source_ad_id):continue
        creative_name=(row.get('creative') or {}).get('name') or ''
        if str(row.get('id')) in persisted or row.get('name')==ad.name or (wanted and (creative_name==wanted or creative_name.startswith(wanted+' '))) or lineage_count==1:
            matches.append(row)
    if not matches:return None,[]
    if len(matches)==1:return matches[0],[]
    ordered=[live[ident] for ident in persisted if ident in live]
    # Only journal-proven successful copies of this same slot may be archived.
    if not ordered or {str(x['id']) for x in ordered}!={str(x['id']) for x in matches}:
        raise ValueError('ambiguous prestaged slot; no write or replay')
    return ordered[0],ordered[1:]
