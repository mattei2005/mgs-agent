from repair_helpers import *
import urllib.request,urllib.error,hashlib,shutil
W=Path(__file__).parent;r=json.loads((W/'git-rewrite-result.json').read_text());ROOT=Path('/root/mgs-agent')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
old='a73a267d04109c85abcb0dea7642b6c3b9736a59';target=r['removed_path']
blob=git('rev-parse',old+':'+target)
# Read at most the archive signature, never dump the response or attach it.
url='https://raw.githubusercontent.com/mattei2005/mgs-agent/'+old+'/'+target
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=0-4'}),timeout=45) as response:
  code=response.status;signature=response.read(5);retained=code in (200,206) and signature==b'PGDMP'
except urllib.error.HTTPError as e:code=e.code;retained=False
r['github_old_commit_raw_http']=code;r['github_old_dump_still_accessible']=retained
(W/'git-rewrite-result.json').write_text(json.dumps(r,indent=2))
print('GITHUB_RETENTION',json.dumps({'old_dump_http':code,'old_dump_still_accessible':retained}))
clone=Path(r['clone']);assert clone.parent==Path('/root/.hermes/profiles/zeus/secure-backups/finance-security-1551287899746598946') and clone.name=='rewrite.git'
shutil.rmtree(clone)
# Drop only unreachable reflog history of the affected branch and HEAD.
for ref in ['HEAD','refs/heads/main','refs/remotes/origin/main']:
 git('reflog','expire','--expire=never','--expire-unreachable=now','--rewrite',ref)
assert not git('log','--all','--reflog','--format=%H','--',target),'Other reflog retains dump; investigate before broader pruning'
git('prune','--expire=now')
p=subprocess.run(['git','cat-file','-e',blob],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
r['local_dump_blob_removed']=p.returncode!=0;r['private_original_backup_preserved']=(ROOT/'apps/finance-system/private/adops-1551275920671776839/before.dump').exists()
assert r['private_original_backup_preserved']
r['status']='branch_clean_credentials_rotated_github_retention_pending' if retained else 'branch_clean_credentials_rotated'
(W/'git-rewrite-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
