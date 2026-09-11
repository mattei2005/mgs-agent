#!/usr/bin/env python3
"""Install or update the GAM intake/finalize schedule after global preflight."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import time

parser=argparse.ArgumentParser();parser.add_argument('--evidence-dir',type=pathlib.Path,default=pathlib.Path('/root/mgs-agent/apps/finance-system/private/gam-automation-1547983130038767755'));args=parser.parse_args()
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');E=args.evidence_dir;proof=E/'schedule-preflight.json';report=json.loads(proof.read_text());assert report['pass'] and report['civil_dates']==8 and not report['operational_conflicts'] and time.time()-proof.stat().st_mtime<1800
before=subprocess.check_output(['crontab','-l'],text=True);script=ROOT/'finance_gam_revenue_sync.py';stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());backup=E/('root-crontab-before-'+stamp+'.txt');backup.parent.mkdir(parents=True,exist_ok=True,mode=0o700);backup.write_text(before);backup.chmod(0o600)
base='\n'.join(line for line in before.splitlines() if str(script) not in line and not line.startswith('# MGS daily GAM revenue email')).rstrip();log=pathlib.Path('/root/mgs-agent/logs/finance-gam-revenue.log');log.touch(exist_ok=True)
intake=report['schedule']+" /usr/bin/flock -n /var/lock/mgs-finance-gam-revenue.cron.lock /bin/sh -c '/bin/sleep 17; /usr/bin/timeout 900s /usr/bin/python3 "+str(script)+" --scheduled-intake >> "+str(log)+" 2>&1'"
finalize=report['finalize_schedule']+" /usr/bin/flock -n /var/lock/mgs-finance-gam-revenue.cron.lock /bin/sh -c '/bin/sleep 17; /usr/bin/timeout 1500s /usr/bin/python3 "+str(script)+" --scheduled-finalize >> "+str(log)+" 2>&1'"
text=base+"\n\n# MGS daily GAM revenue email intake; authorization1547983130038767755; Eastern 08:00-08:30\n"+intake+"\n# MGS daily GAM revenue finalize after spend; audit1548008533608636527\n"+finalize+"\n";subprocess.run(['crontab','-'],input=text,text=True,check=True);actual=subprocess.check_output(['crontab','-l'],text=True);assert actual==text and actual.count(str(script))==2 and actual.count(intake)==1 and actual.count(finalize)==1
contract_path=pathlib.Path('/root/mgs-agent/data/finance-gam-revenue-contract.json');contract=json.loads(contract_path.read_text());assert contract['schedule']==report['schedule'] and contract['poll_minutes']==report['poll_minutes'] and contract['finalize_schedule']==report['finalize_schedule'] and contract['finalize_minutes']==report['finalize_minutes'];contract.update({'cron':intake,'cron_finalize':finalize,'cron_entries':[intake,finalize],'preflight':str(proof),'crontab_sha256':hashlib.sha256(actual.encode()).hexdigest(),'crontab_backup':str(backup),'schedule_readback':True,'schedule_installed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});temporary=contract_path.with_name(contract_path.name+'.pending');temporary.write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n');temporary.chmod(0o600);os.replace(temporary,contract_path);evidence={'pass':True,'schedule':report['schedule'],'poll_minutes':report['poll_minutes'],'finalize_schedule':report['finalize_schedule'],'finalize_minutes':report['finalize_minutes'],'cron_entries':[intake,finalize],'crontab_sha256':contract['crontab_sha256'],'other_entries_preserved':True,'backup':str(backup)};(E/'schedule-installed.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':True,'intake':report['schedule'],'finalize':report['finalize_schedule'],'timezone':'America/New_York','entries':2,'other_entries_preserved':True,'contract':str(contract_path)}))
