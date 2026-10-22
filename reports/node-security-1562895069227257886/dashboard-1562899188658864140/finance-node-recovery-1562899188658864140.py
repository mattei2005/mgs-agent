# Runs after the dashboard executor definitions; original receipts stay immutable.
assert not (B/'recovery-start.json').exists(),'recovery already attempted: reconcile'
before=json.loads((B/'preflight.json').read_text())
failed=json.loads((B/'cutover-failure.json').read_text());rollback=json.loads((B/'rollback-result.json').read_text())
assert failed['message']=='unexpected executable' and rollback['exit']==0 and rollback['sha256']==OLD_SHA
assert sha(LIVE)==OLD_SHA and sha(CANDIDATE)==NEW_SHA
assert run([str(LIVE),'--version']).stdout.strip()=='v22.23.2'
assert code_hashes()==before['code'] and deps_hashes()==before['dependencies'] and config_hashes()==before['config']
assert run(['sha256sum','-c',str(B/'rollback.sha256')]).returncode==0
lock=(R/'private/release-control/files.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
try:
 consumers=running_live_consumers();assert len(consumers)==1 and consumers[0]['pid']==int(unit(UNIT)['MainPID'])
 fingerprint=financial_fingerprint();save('recovery-financial-before',fingerprint)
 save('recovery-start',{'authorization':AUTH,'model_exception':EXCEPTION,'time':time.time(),'old_running_pid':unit(UNIT)['MainPID'],'reason':'Original validator sampled immediately after Type=simple restart;bounded readiness records actual executable/version convergence before acceptance.'})
 staged=LIVE.parent/('.node-security-recovery-'+EXCEPTION);assert not staged.exists();shutil.copy2(CANDIDATE,staged);os.chown(staged,before['node_stat']['uid'],before['node_stat']['gid']);staged.chmod(before['node_stat']['mode']);assert sha(staged)==NEW_SHA
 os.replace(staged,LIVE);os.sync();p=run(['systemctl','restart',UNIT],t=70);save('recovery-restart',{'exit':p.returncode,'time':time.time()});assert p.returncode==0
 result=validate(before,fingerprint);result['recovery']='First attempt automatically rolled back;bounded process readiness and full validation succeeded on same approved binary patch.';save('recovery-completion',result);print(json.dumps({'ok':True,'result':result,'readiness':json.loads((B/'latest-runtime-readiness.json').read_text())}))
except Exception as e:
 save('recovery-failure',{'type':type(e).__name__,'error':str(e),'time':time.time(),'disk_sha256':sha(LIVE)})
 if sha(LIVE)==NEW_SHA:
  backup=B/'node-22.23.2-before';assert sha(backup)==OLD_SHA;temp=LIVE.parent/('.node-rollback-recovery-'+EXCEPTION);assert not temp.exists();shutil.copy2(backup,temp);os.chown(temp,before['node_stat']['uid'],before['node_stat']['gid']);temp.chmod(before['node_stat']['mode']);os.replace(temp,LIVE);p=run(['systemctl','restart',UNIT],t=70);save('recovery-rollback',{'exit':p.returncode,'time':time.time(),'http':http()})
 raise
finally:lock.close()
