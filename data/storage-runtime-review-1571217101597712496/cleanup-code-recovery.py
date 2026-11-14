#!/usr/bin/env python3
"""Exercise retained code recovery without importing old code or restoring live state."""
import pathlib,json,tarfile,hashlib,subprocess,os,argparse,datetime
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['before','after'],required=True);a=p.parse_args();OUT=pathlib.Path(__file__).resolve().parent;m=json.loads((OUT/'deletion-manifest.json').read_text());cap=json.load(open(m['code_preservation_manifest']));expected=json.load(open(OUT/'cleanup-recovery-expected.json'))['files'];scratch=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/runtime-delete-replay-1571231699172462614')/a.phase;os.umask(0o077);scratch.mkdir(parents=True,mode=0o700,exist_ok=True)
def run(args):return subprocess.run(args,capture_output=True,check=True)
def sha(p):return run(['sha256sum',str(p)]).stdout.decode().split()[0]
code={}
with tarfile.open(m['code_archive'],'r:gz')as tf:
 for member in tf:
  if member.name=='stage-working-tree.patch'or member.name.startswith(('stage-overlay/','nested-overlay/')):
   f=tf.extractfile(member);assert f is not None;code[member.name]=f.read()
stage=scratch/'stage-modified';stage.mkdir(exist_ok=True);gitbase=m['git_recovery_bases'][0]
for rel in cap['stage_modified_paths']:
 q=stage/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(run(['git','-C',gitbase['repository'],'show',gitbase['commit']+':'+rel]).stdout);mode=run(['git','-C',gitbase['repository'],'ls-tree',gitbase['commit'],'--',rel]).stdout.split()[0];os.chmod(q,0o755 if mode==b'100755'else 0o644)
patch=scratch/'stage-working-tree.patch';patch.write_bytes(code['stage-working-tree.patch']);run(['git','-C',str(stage),'apply','--check',str(patch)]);run(['git','-C',str(stage),'apply',str(patch)])
for name,data in code.items():
 for prefix,folder in [('stage-overlay/','stage-overlay'),('nested-overlay/','nested-overlay')]:
  if name.startswith(prefix):q=scratch/folder/name[len(prefix):];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
venv_archive=pathlib.Path(m['code_archive']).with_name('old-venv-local-overrides.tar.gz')
with tarfile.open(venv_archive,'r:gz')as tf:
 for member in tf:
  if not member.isfile():continue
  f=tf.extractfile(member);assert f is not None;q=scratch/'venv-override'/member.name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(f.read())
checked=0
for r in expected:
 q=scratch/r['area']/r['path'];assert q.is_file()and sha(q)==r['sha256']and q.stat().st_size==r['size'],'Focused recovered payload mismatch';checked+=1
# Complete original nested checksum proof, using only a retained Git tree plus overlays.
hashes={};base=m['git_recovery_bases'][1];proc=subprocess.Popen(['git','-C',base['repository'],'archive','--format=tar',base['commit']],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert proc.stdout is not None
with tarfile.open(fileobj=proc.stdout,mode='r|')as tf:
 for member in tf:
  if not member.isfile():continue
  f=tf.extractfile(member);assert f is not None;h=hashlib.sha256()
  while chunk:=f.read(1024*1024):h.update(chunk)
  hashes[member.name]=h.hexdigest()
assert proc.stderr is not None;stderr=proc.stderr.read();assert proc.wait()==0
for name,data in code.items():
 if name.startswith('nested-overlay/'):hashes[name[len('nested-overlay/'):]]=hashlib.sha256(data).hexdigest()
parent=pathlib.Path(m['targets'][1]['path']).parent;rows=0
for line in (parent/'EVIDENCE-SHA256SUMS').read_text().splitlines():
 marker='clean-target-7cc3fb8c/'
 if marker not in line:continue
 h,name=line.split(None,1);rel=name.split(marker,1)[1];assert hashes.get(rel)==h,'Historical original code checksum mismatch';rows+=1
assert rows==18319
result={'phase':a.phase,'status':'PASS','focused_recovered_files':checked,'stage_modified':sum(r['area']=='stage-modified'for r in expected),'stage_extra_and_ignored':sum(r['area']=='stage-overlay'for r in expected),'nested_changed_extra':sum(r['area']=='nested-overlay'for r in expected),'old_venv_local_overrides':sum(r['area']=='venv-override'for r in expected),'nested_original_checksum_rows_reconstructed':rows,'candidate_sources_read':False,'full_old_venv_rebuilt':False,'production_code_imported':False,'live_profile_or_sqlite_opened':False,'scratch':str(scratch),'observed_at':datetime.datetime.now().astimezone().isoformat()};(OUT/f'cleanup-code-recovery-{a.phase}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
