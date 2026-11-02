#!/usr/bin/env python3
"""Read-only native tree inventory; checkpointed batches and no Drive writes."""
import json,sys,collections,hashlib
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
OUT=b.BASE/'data/ares/creative-ops/30tb-archive/two-drive-audit-1566810303168254075'
OUT.mkdir(exist_ok=True,parents=True)
ROOTS={'mgs':'0AEwt4Ye690ocUk9PVA','archive':'1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J','corporate':'16fP9b4bp3inB1Gze95znQLYq3rdtTEhp'}
FIELDS='id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,createdTime,modifiedTime,owners(emailAddress,permissionId),lastModifyingUser(emailAddress,permissionId),properties,shortcutDetails(targetId),trashed'
d=b.Drive(False)
mode=sys.argv[1]
if mode in ['mgs','owner']:
 statepath=OUT/(mode+'-enumeration-state.json');state=b.read_json(statepath,{'nextPageToken':None,'pages':0,'complete':False})
 if state['complete']:print(json.dumps({'mode':mode,'already_complete':True,'pages':state['pages']}));sys.exit()
 for _ in range(6):
  params={'q':'trashed=false','pageSize':1000,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','fields':'files('+FIELDS+'),nextPageToken,incompleteSearch'}
  if mode=='mgs':params.update(corpora='drive',driveId=ROOTS['mgs'])
  else:params.update(corpora='user',q="trashed=false and 'mgsdigitalcorp@gmail.com' in owners")
  if state['nextPageToken']:params['pageToken']=state['nextPageToken']
  result=d.api('GET','files',params)
  if result.get('incompleteSearch'):raise RuntimeError('INCOMPLETE_NATIVE_SEARCH')
  batch=result.get('files',[]);b.atomic_json(OUT/(mode+'-page-'+str(state['pages']+1)+'.json'),batch)
  state.update(pages=state['pages']+1,nextPageToken=result.get('nextPageToken'),complete=not result.get('nextPageToken'),observed_at=b.now_iso());b.atomic_json(statepath,state)
  print(json.dumps({'mode':mode,'page':state['pages'],'objects':len(batch),'complete':state['complete']}))
  if state['complete']:break
elif mode=='aggregate':
 bymode={}
 for key in ['mgs','owner']:
  state=b.read_json(OUT/(key+'-enumeration-state.json'));assert state['complete']
  by={}
  for num in range(1,state['pages']+1):
   for x in b.read_json(OUT/(key+'-page-'+str(num)+'.json')):
    if x['id'] in by and by[x['id']]!=x:raise RuntimeError('PAGINATION_DRIFT:'+x['id'])
    by[x['id']]=x
  bymode[key]=by
 allnodes={**bymode['mgs'],**bymode['owner']}
 for label,rid in ROOTS.items():
  if label!='mgs':allnodes[rid]=d.api('GET','files/'+rid,{'supportsAllDrives':'true','fields':FIELDS})
 kids=collections.defaultdict(list)
 for node in allnodes.values():
  for parent in node.get('parents',[]):kids[parent].append(node['id'])
 def descend(root):
  seen=set();stack=list(kids[root])
  while stack:
   fid=stack.pop()
   if fid in seen:continue
   seen.add(fid)
   if allnodes[fid]['mimeType']==b.FOLDER:stack.extend(kids[fid])
  return seen
 summary={};corpus={};folderrows=[]
 for label,rid in ROOTS.items():
  members=descend(rid);corpus[label]=sorted(members);folders={i for i in members if allnodes[i]['mimeType']==b.FOLDER}
  summary[label]={'root_id':rid,'root_name':allnodes.get(rid,{}).get('name','MGS-AGENTS'),'objects':len(members),'folders':len(folders),'files':len(members-folders),'root_children':[{'id':i,'name':allnodes[i]['name'],'mimeType':allnodes[i]['mimeType'],'descendant_objects':len(descend(i)) if i in folders else 0,'descendant_folders':sum(allnodes[x]['mimeType']==b.FOLDER for x in descend(i)) if i in folders else 0} for i in sorted(kids[rid],key=lambda i:allnodes[i]['name'])]}
  def path(fid):
   names=[];seen=set()
   while fid!=rid:
    if fid in seen:raise RuntimeError('PARENT_CYCLE')
    seen.add(fid);n=allnodes[fid];names.append(n['name']);ps=n.get('parents',[])
    if len(ps)!=1:raise RuntimeError('AMBIGUOUS_PARENT')
    fid=ps[0]
   return '/'.join(reversed(names))
  for fid in folders:folderrows.append({'scope':label,'id':fid,'path':path(fid),'parent_ids':allnodes[fid].get('parents',[]),'direct_objects':len(kids[fid]),'direct_files':sum(allnodes[x]['mimeType']!=b.FOLDER for x in kids[fid])})
 owned=descend(ROOTS['archive'])|descend(ROOTS['corporate'])|{ROOTS['archive'],ROOTS['corporate']}
 outside=[{'id':i,'name':n['name'],'mimeType':n['mimeType'],'parents':n.get('parents',[])} for i,n in bymode['owner'].items() if i not in owned]
 b.atomic_json(OUT/'all-native-objects.json',allnodes);b.atomic_json(OUT/'folder-paths.json',sorted(folderrows,key=lambda x:(x['scope'],x['path'])));b.atomic_json(OUT/'corpus-membership.json',corpus)
 result={'schema':'mgs.two.drive.tree.audit.v1','observed_at':b.now_iso(),'complete_pages':True,'summary':summary,'owner_visible_outside_mgs_roots':outside,'owner_scope_limit':'SA-visible owner-account objects; complete known MGS roots, not a claim about unshared personal-account items','remote_writes':0}
 b.atomic_json(OUT/'tree-summary.json',result)
 print(json.dumps(result,ensure_ascii=False))
else:raise SystemExit('unknown mode')
