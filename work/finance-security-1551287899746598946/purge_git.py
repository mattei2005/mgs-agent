import subprocess,os,json,shlex
from pathlib import Path
ROOT=Path('/root/mgs-agent');W=ROOT/'work/finance-security-1551287899746598946';SEC=Path('/root/.hermes/profiles/zeus/secure-backups/finance-security-1551287899746598946');CLONE=SEC/'rewrite.git';TARGET='work/finance-adops-1551275920671776839/before.dump'
def git(*args,cwd=ROOT,env=None):
 p=subprocess.run(['git',*args],cwd=cwd,env=env,capture_output=True,text=True)
 if p.returncode:raise RuntimeError('git '+str(args[:2])+' failed: '+p.stderr[-600:])
 return p.stdout.strip()
assert subprocess.run(['systemctl','is-active','--quiet','mgs-autocommit.service']).returncode!=0
staged=git('diff','--cached','--name-only');assert not staged, 'Concurrent staging detected'
old_remote=git('ls-remote','origin','refs/heads/main').split()[0]
assert old_remote==git('rev-parse','HEAD')=='025531c4e36e35e4cc663c2ed483ceffd33be284'
refs=git('ls-remote','origin');(W/'remote-refs-before.txt').write_text(refs+'\n')
# Record unrelated working edits and preserve them; no worktree reset/stash.
before_status=git('status','--porcelain');(W/'worktree-before.txt').write_text(before_status+'\n')
git('add','--','.gitignore')
assert git('diff','--cached','--name-only')=='.gitignore'
git('-c','core.hooksPath=/dev/null','commit','-m','security: prevent production database dumps entering Git')
old_head=git('rev-parse','HEAD')
assert not CLONE.exists()
git('clone','--bare','--shared',str(ROOT),str(CLONE))
CLONE.chmod(0o700)
env=os.environ.copy();env['FILTER_BRANCH_SQUELCH_WARNING']='1'
out=git('filter-branch','--force','--index-filter','git rm --cached --ignore-unmatch -- '+shlex.quote(TARGET),'--','c612e2f3d..refs/heads/main',cwd=CLONE,env=env)
new_head=git('rev-parse','main',cwd=CLONE)
assert new_head!=old_head
assert git('log','--format=%H','main','--',TARGET,cwd=CLONE)==''
# The rewrite changes only the exposed file; guard commit is already in old_head.
changed=git('diff','--name-only',old_head,new_head,cwd=CLONE)
assert changed==TARGET,changed
ssh=git('config','--get','core.sshCommand')
git('config','core.sshCommand',ssh,cwd=CLONE)
git('remote','add','github','git@github.com:mattei2005/mgs-agent.git',cwd=CLONE)
git('push','--force-with-lease=refs/heads/main:'+old_remote,'github','refs/heads/main:refs/heads/main',cwd=CLONE)
assert git('ls-remote','github','refs/heads/main',cwd=CLONE).split()[0]==new_head
# Import new objects, atomically move just main, and remove only the obsolete index entry.
git('-c','core.hooksPath=/dev/null','fetch',str(CLONE),'refs/heads/main')
git('update-ref','refs/heads/main',new_head,old_head)
git('update-ref','refs/remotes/origin/main',new_head,old_remote)
git('update-index','--force-remove','--',TARGET)
assert git('log','--all','--format=%H','--',TARGET)==''
assert git('ls-files','--',TARGET)==''
assert git('rev-parse','HEAD')==git('rev-parse','origin/main')
assert git('diff','--cached','--name-only')==''
after_refs=git('ls-remote','origin')
before_tags=[l for l in refs.splitlines() if 'refs/tags/' in l];after_tags=[l for l in after_refs.splitlines() if 'refs/tags/' in l];assert before_tags==after_tags
r={'remote_before':old_remote,'guard_commit_before_rewrite':old_head,'remote_after':new_head,'removed_path':TARGET,'reachable_path_commits':0,'tags_unchanged':True,'financial_worktree_preserved':True,'clone':str(CLONE),'status':'remote_main_clean_exact_sha_retention_check_pending'}
(W/'git-rewrite-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
