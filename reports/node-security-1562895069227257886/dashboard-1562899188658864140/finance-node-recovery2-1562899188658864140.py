# Final same-scope recovery after two verified automatic rollbacks.
assert not (B/'recovery2-start.json').exists(),'attempt exists: reconcile'
previous=json.loads((B/'recovery-failure.json').read_text());previous_rollback=json.loads((B/'recovery-rollback.json').read_text())
assert previous['type']=='KeyError' and previous['error']=="'MainPID'" and previous_rollback['exit']==0
before=json.loads((B/'preflight.json').read_text())
assert sha(LIVE)==OLD_SHA and sha(CANDIDATE)==NEW_SHA
assert run([str(LIVE),'--version']).stdout.strip()=='v22.23.2'
assert code_hashes()==before['code'] and deps_hashes()==before['dependencies'] and config_hashes()==before['config']
assert run(['sha256sum','-c',str(B/'rollback.sha256')]).returncode==0
for name,value in {name:unit(name) for name in PROTECTED}.items():
 assert value['ActiveState']=='active' and value.get('MainPID')==before['protected'][name].get('MainPID')
lock=(R/'private/release-control/files.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
try:
 consumers=running_live_consumers();assert len(consumers)==1 and consumers[0]['pid']==int(unit(UNIT)['MainPID'])
 fingerprint=financial_fingerprint();save('recovery2-financial-before',fingerprint)
 save('recovery2-start',{'authorization':AUTH,'model_exception':EXCEPTION,'time':time.time(),'old_pid':unit(UNIT)['MainPID'],'corrections':'bounded Type=simple executable convergence;socket unit correctly validated without nonexistent MainPID'})
 staged=LIVE.parent/('.node-security-recovery2-'+EXCEPTION);assert not staged.exists();shutil.copy2(CANDIDATE,staged);os.chown(staged,before['node_stat']['uid'],before['node_stat']['gid']);staged.chmod(before['node_stat']['mode']);assert sha(staged)==NEW_SHA
 os.replace(staged,LIVE);os.sync();p=run(['systemctl','restart',UNIT],t=70);save('recovery2-restart',{'exit':p.returncode,'time':time.time()});assert p.returncode==0
 result=validate(before,fingerprint);result['recovered_validator_failures']=['Type=simple briefly exposes systemd executable before Node exec;actual convergence recorded','Socket units have ActiveState but no MainPID;role-aware checks passed before retry'];save('recovery2-completion',result);print(json.dumps({'ok':True,'result':result,'readiness':json.loads((B/'latest-runtime-readiness.json').read_text())}))
except Exception as error:
 save('recovery2-failure',{'type':type(error).__name__,'error':str(error),'time':time.time(),'disk_sha256':sha(LIVE)})
 if sha(LIVE)==NEW_SHA:
  backup=B/'node-22.23.2-before';assert sha(backup)==OLD_SHA;temp=LIVE.parent/('.node-rollback-recovery2-'+EXCEPTION);assert not temp.exists();shutil.copy2(backup,temp);os.chown(temp,before['node_stat']['uid'],before['node_stat']['gid']);temp.chmod(before['node_stat']['mode']);os.replace(temp,LIVE);p=run(['systemctl','restart',UNIT],t=70);save('recovery2-rollback',{'exit':p.returncode,'time':time.time(),'http':http()})
 raise
finally:lock.close()
