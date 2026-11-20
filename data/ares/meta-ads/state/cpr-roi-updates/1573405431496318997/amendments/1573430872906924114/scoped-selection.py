def discover(r,m,run,ac):
 z=ZoneInfo(m['timezone_name']);end=datetime.fromisoformat(m['edit_cutoff']);begin=datetime.combine(datetime.fromisoformat(m['date']).date(),datetime.min.time(),z)
 cs=r.source(run,'discovery-campaigns',lambda:r.paged('act_'+AID+'/campaigns',{'fields':META_FIELDS,'filtering':json.dumps([{'field':'effective_status','operator':'IN','value':['ACTIVE','PAUSED','ARCHIVED','IN_PROCESS','WITH_ISSUES']}]),'limit':500}))
 cm={c['id']:c for c in cs};assert len(cm)==len(cs) and all(c['account_id']==AID for c in cs)
 edit_end=min(end,datetime.fromisoformat(m['edit_cutoff']))
 data=r.source(run,'activities',lambda:dict(zip(['events','pages'],ac.fetch_activities(r.meta,r.token,AID,begin,edit_end,40)))) if not m.get('edits_frozen') else {'events':[],'pages':[]}
 assert not data['pages'] or not data['pages'][-1]['has_next']
 material=[e for e in data['events'] if event_material(e,begin,edit_end)]
 # Resolve current hierarchy from immutable object IDs, not legacy object labels/names.
 objects={str(e['object_id']):e.get('object_type') for e in material if str(e['object_id']) not in cm}
 child_ids=sorted(cid for cid,typ in objects.items() if typ in ('CAMPAIGN','ADGROUP'))
 children=r.source(run,'hierarchy-children',lambda:batch(r,child_ids,'id,account_id,campaign_id')[0]) if child_ids else {}
 parents={str(c['campaign_id']) for c in children.values()}
 parents|={str(e['object_id']) for e in data['events'] if e.get('event_type')=='create_campaign_group' and begin<=datetime.fromisoformat(e['event_time'])<=end}
 parents|={cid for cid,typ in objects.items() if typ=='CAMPAIGN_GROUP'}
 parents|={c['id'] for c in m.get('campaigns',[])}
 absent=sorted(parents-set(cm))
 recovered,missing=r.source(run,'hierarchy-campaigns',lambda:batch(r,absent,META_FIELDS,True)) if absent else ({},[])
 cm.update(recovered)
 admitted={c['id']:dict(c) for c in m.get('campaigns',[])};reasons={cid:set(c.get('reasons',[])) for cid,c in admitted.items()}
 for c in cm.values():
  if candidate(c,m,end):reasons.setdefault(c['id'],set()).add('created_today')
 evidence=[]
 for e in material:
  oid=str(e['object_id']);cid=oid if oid in cm else str(children.get(oid,{}).get('campaign_id',''))
  if not cid and oid in missing:continue
  assert cid and cid in cm,'Unresolved material change parent'
  reasons.setdefault(cid,set()).add('changed_today')
  evidence.append({'campaign_id':cid,'event_time':e['event_time'],'event_type':e['event_type'],'actor_id':e.get('actor_id'),'application_id':e.get('application_id')})
 for cid,why in reasons.items():
  c=dict(cm.get(cid,admitted.get(cid,{})));assert c and c['account_id']==AID
  number=c['name'].split(' - ')[0];assert number.isdigit(),'Unresolved number'
  admitted[cid]={**c,'number':number,'reasons':sorted(why)}
 save(run/'membership-evidence.json',{'material_events':evidence,'missing_campaigns':missing,'activities_pages':data['pages'],'observed_at':end.isoformat()})
 return admitted,cm,missing