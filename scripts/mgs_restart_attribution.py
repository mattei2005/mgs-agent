"""Read-only restart attribution: operation receipt + exact PID, then host boot.
A Monarx agent starting is not evidence of a package update.
"""
from __future__ import annotations
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


def ts(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError):
        return None


def infer(svc, epoch, journal, *, boot_epoch=None, pid=None, receipts=None):
    if boot_epoch is None:
        try:
            boot_epoch = int(next(l.split()[1] for l in Path('/proc/stat').read_text().splitlines() if l.startswith('btime ')))
        except (OSError, StopIteration, ValueError):
            boot_epoch = 0
    if receipts is None:
        root = Path('/root/.hermes/secure-backups/hermes-update')
        receipts = []
        for p in sorted(root.glob('*/post-activation-result.json'))[-5:]:
            try:
                receipts.append(json.loads(p.read_text()))
            except (OSError, ValueError):
                pass
    if pid is None:
        p = subprocess.run(['systemctl', 'show', svc, '-p', 'MainPID', '--value'], capture_output=True, text=True, timeout=10)
        pid = p.stdout.strip() if p.returncode == 0 else ''
    for receipt in receipts:
        target = (receipt.get('gateways') or {}).get(svc.removesuffix('-gateway'), {})
        start, end = ts(receipt.get('started_at')), ts(receipt.get('validated_at'))
        if (receipt.get('status') == 'completed' and receipt.get('runtime_validated') is True
                and start is not None and end is not None and start - 60 <= epoch <= end + 60
                and str(target.get('pid')) == str(pid) and target.get('active') and target.get('code_matches')):
            return 'Ativação Hermes validada no registro pós-update; PID e janela correspondem ao serviço.'
    if boot_epoch and 0 <= epoch - boot_epoch <= 600:
        return 'Reboot do host confirmado pelo boot atual; início de serviço próximo ao boot. Consultar registro de manutenção para autorização.'
    if re.search(r'apt-get\s+(?:[^\n]*\s)?install[^\n]*monarx|monarx-update[^\n]*(?:execut|running)', journal, re.I):
        return 'Atualização do pacote Monarx evidenciada na janela; verificar autorização e janela real (não inferida pelo start do agente).'
    if re.search(r'needrestart|apt-get|unattended-upgrade|packagekit', journal, re.I):
        return 'Atualização de pacote/needrestart evidenciada; confirmar manutenção no registro.'
    return 'Causa não atribuída: nenhum registro de ativação/PID, boot ou execução de atualização corresponde; investigar journal.'


if __name__ == '__main__':
    import sys
    print(infer(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
