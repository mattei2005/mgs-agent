"""Resumable reference census. Store positive path tokens only, never source/business/credential bodies."""
import pathlib,json,gzip,re,time,hashlib,os,argparse
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;M=json.loads((O/'metadata-summary.json').read_text());P=pathlib.Path(M['own_analysis_excluded'][1]);sources=json.load(gzip.open(P/'consumer-source-index.json.gz','rt'));finance=json.loads((P/'closed-candidate-copied-json-selection.json').read_text());media=json.loads((O/'historical-media-archive-join.json').read_text())['matches'];targets=[r['path']for r in finance+media];aliases={p:p for p in targets}
for p in targets:
 if p.startswith(str(R/'apps/finance-system')+'/'):aliases[p[len(str(R/'apps/finance-system'))+1:]]=p
roots=sorted({'/'.join(p.split('/')[:8])for p in targets if p.startswith('/root/.hermes/profiles/ares/work/')}|{'/root/.hermes/profiles/ares/artifacts/meta-library'});kind={k:'target'for k in aliases}
for p in roots:aliases[p]=p;kind[p]='media_root_selector'
pattern=re.compile(b'|'.join(re.escape(p.encode())for p in sorted(aliases,key=lambda s:-len(s))));progress=O/'consumer-scan-progress.json';state=json.loads(progress.read_text())if progress.exists()else{'covered_until':0,'total_sources':len(sources),'positives':0,'unavailable':0,'native_changed_since_index':0};assert state['total_sources']==len(sources);ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=70000);args=ap.parse_args();start=time.monotonic();begin=state['covered_until'];end=min(len(sources),begin+args.limit);positive=[];errors=[]
for i in range(begin,end):
 if i>begin and i%500==0 and time.monotonic()-start>100:break
 row=sources[i];p=row['path']
 try:data=pathlib.Path(p).read_bytes()
 except OSError as e:errors.append({'index':i,'path':p,'error':type(e).__name__,'native_code_config':row['native_executable_or_config']});state['unavailable']+=1;state['covered_until']=i+1;continue
 found={m.group().decode()for m in pattern.finditer(data)}
 if found:
  digest=hashlib.sha256(data).hexdigest();positive.append({'source':p,'sha256':digest,'native_code_config':row['native_executable_or_config'],'matches':[{'token':t,'target':aliases[t],'kind':kind[t]}for t in sorted(found)],'source_suffix':pathlib.PurePosixPath(p).suffix,'matching_line_numbers':[n for n,line in enumerate(data.splitlines(),1)if any(t.encode()in line for t in found)][:30]})
 if row['native_executable_or_config']and row.get('native_sha256')!=hashlib.sha256(data).hexdigest():state['native_changed_since_index']+=1
 state['covered_until']=i+1
with(P/'consumer-reference-hits.jsonl').open('a')as f:
 for row in positive:f.write(json.dumps(row)+'\n')
 f.flush();os.fsync(f.fileno())
with(P/'consumer-unavailable-observations.jsonl').open('a')as f:
 for row in errors:f.write(json.dumps(row)+'\n')
 f.flush();os.fsync(f.fileno())
state['positives']+=len(positive);progress.write_text(json.dumps(state,indent=2)+'\n');print(json.dumps({**state,'new_sources_read_or_disclosed':state['covered_until']-begin,'remaining':len(sources)-state['covered_until'],'source_files_deleted':0}))
