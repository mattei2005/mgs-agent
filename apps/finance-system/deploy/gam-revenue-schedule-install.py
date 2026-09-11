#!/usr/bin/env python3
"""Install the approved GAM email schedule after global collision preflight."""
import hashlib
import json
import os
import pathlib
import subprocess
import time

ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');E=ROOT/'private/gam-automation-1547983130038767755';proof=E/'schedule-preflight.json';report=json.loads(proof.read_text());assert report['pass'] and report['civil_dates']==8 and not report['operational_conflicts'] and time.time()-proof.stat().st_mtime<1800
before=subprocess.check_output(['crontab','-l'],text=True);script=ROOT/'finance_gam_revenue_sync.py';assert str(script) not in before
backup=E/'root-crontab-before.txt';backup.write_text(before);backup.chmod(0o600)
log=pathlib.Path('/root/mgs-agent/logs/finance-gam-revenue.log');log.touch(exist_ok=True)
line=report['schedule']+" /usr/bin/flock -n /var/lock/mgs-finance-gam-revenue.cron.lock /bin/sh -c '/bin/sleep 17; /usr/bin/timeout 1500s /usr/bin/python3 "+str(script)+" --scheduled >> "+str(log)+" 2>&1'"
text=before.rstrip()+"\n\n# MGS daily GAM revenue email; authorization1547983130038767755; Eastern 08:00-08:30; global8-day preflight\n"+line+"\n";subprocess.run(['crontab','-'],input=text,text=True,check=True);actual=subprocess.check_output(['crontab','-l'],text=True);assert actual==text and actual.count(str(script))==1
contract_path=pathlib.Path('/root/mgs-agent/data/finance-gam-revenue-contract.json');contract=json.loads(contract_path.read_text());assert contract['schedule']==report['schedule'] and contract['poll_minutes']==report['poll_minutes'];contract.update({'cron':line,'crontab_sha256':hashlib.sha256(actual.encode()).hexdigest(),'crontab_backup':str(backup),'schedule_readback':True,'schedule_installed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});temporary=contract_path.with_name(contract_path.name+'.pending');temporary.write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n');temporary.chmod(0o600);os.replace(temporary,contract_path);(E/'schedule-installed.json').write_text(json.dumps({'pass':True,'schedule':report['schedule'],'poll_minutes':report['poll_minutes'],'cron':line,'crontab_sha256':contract['crontab_sha256'],'other_entries_preserved':True},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':True,'schedule':report['schedule'],'poll_minutes':report['poll_minutes'],'timezone':'America/New_York','unique_entry':True,'other_entries_preserved':True,'contract':str(contract_path)}))
