#!/usr/bin/env python3
"""Forced-command guest collector. Only a fixed read-only operation is accepted."""
import json
import os
import subprocess
import sys
import time

UNITS=('nginx-rc.service','mariadb.service','apache2-rc.service','supervisord.service','redis-server.service','redis.service')
COMMAND='mgs-health-v1'

def collect():
    fs=os.statvfs('/')
    total=fs.f_blocks*fs.f_frsize/1048576
    available=fs.f_bavail*fs.f_frsize/1048576
    used=(fs.f_blocks-fs.f_bfree)*fs.f_frsize/1048576
    services={}
    for unit in UNITS:
        p=subprocess.run(['/usr/bin/systemctl','show',unit,'-p','LoadState','-p','ActiveState','--no-pager'],capture_output=True,text=True,timeout=5,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        fields=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
        services[unit]={'load':fields.get('LoadState','unknown'),'active':fields.get('ActiveState','unknown')}
    return {'schema':1,'checked_at':time.time(),'disk':{'total_mb':total,'used_mb':used,'available_mb':available},'services':services}

def main():
    if os.environ.get('SSH_ORIGINAL_COMMAND')!=COMMAND or os.environ.get('SSH_TTY'):
        print('Access denied: read-only monitor command only.',file=sys.stderr)
        return 126
    try:
        print(json.dumps(collect(),allow_nan=False));return 0
    except (OSError,ValueError,subprocess.SubprocessError):
        print('Read-only monitoring collection failed.',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
