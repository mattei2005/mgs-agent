#!/usr/bin/env python3
"""Postactivation real native registry smoke in the exact Zeus profile; GET-only."""
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
import yaml

REPO = Path('/root/.local/bin/hermes').resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
from tools.mcp_tool_discovery import register_mcp_servers
from tools.mcp_tool_lifecycle import shutdown_mcp_servers
from tools.mcp_tool_handlers import _trust_gate_check
from tools.registry import registry

WORK = Path(__file__).parent
HOME = Path(os.environ['HERMES_HOME'])
assert HOME == Path('/root/.hermes/profiles/zeus')
config = yaml.safe_load(Path('/root/.hermes/profiles/zeus/config.yaml').read_text())['mcp_servers']['hostinger-vps']
assert config['trust'] == 'untrusted'


def call(raw_name, args, *, denied=False):
    name = next(n for n in names if n.endswith('__' + raw_name.replace('-', '_')))
    assert _trust_gate_check('hostinger-vps', raw_name) is None
    raw = registry.dispatch(name, args)
    outer = json.loads(raw) if isinstance(raw, str) else raw
    if denied:
        # A circuit-breaker refusal is NOT evidence that the adapter blocked a mutation.
        assert 'Unknown operation' in str(outer.get('error', '')), ('Missing catalog denial', raw_name)
        return {'denied': True}
    assert 'error' not in outer and not outer.get('isError') and not outer.get('is_error'), ('Read-only call failed', raw_name)
    result = outer['result']
    return json.loads(result) if isinstance(result, str) else result


try:
    names = register_mcp_servers({'hostinger-vps': config})
    assert len(names) == 3
    now = datetime.now(timezone.utc)
    receipt = {'observed_at': now.isoformat(), 'runtime': str(REPO), 'trust': config['trust'],
               'native_registry': True, 'fresh_postactivation_profile_process': True, 'active_gateway_validation': False,
               'tools': names, 'operations': {}}
    result = call('search', {'query': 'vps', 'limit': 5})
    assert 'vps_virtual-machines_get' in json.dumps(result)
    operations = ['vps_virtual-machines_get', 'vps_virtual-machines_metrics', 'vps_backups_list', 'vps_snapshots_get', 'vps_actions_list']
    for op in operations:
        params = {}
        if op.endswith('_metrics'):
            params = {'date_from': (now-timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'), 'date_to': now.strftime('%Y-%m-%dT%H:%M:%SZ')}
        value = call('execute', {'operation': op, 'params': params})
        if op == 'vps_virtual-machines_get':
            assert value['id'] == 1767265 and value['hostname'] == 'srv1767265.hstgr.cloud'
            receipt['vps'] = {k: value[k] for k in ['id', 'hostname', 'state']}
        receipt['operations'][op] = {'pass': True}
    batch = call('multi-execute', {'steps': [{'operation': 'vps_virtual-machines_get', 'params': {}}, {'operation': 'vps_snapshots_get', 'params': {}}]})
    assert '1767265' in json.dumps(batch)
    receipt['batch_get'] = True
    fixed = call('execute', {'operation': 'vps_virtual-machines_get', 'params': {'virtualMachineId': 1}})
    assert fixed['id'] == 1767265
    forbidden = ['vps_virtual-machines_restart', 'vps_virtual-machines_stop', 'vps_backups_restore', 'vps_firewall_create', 'billing_orders_create']
    for op in forbidden:
        call('execute', {'operation': op, 'params': {}}, denied=True)
        # Expected guard errors also feed Hermes' circuit breaker. Prove recovery by an
        # ordinary authorized GET, never by disabling/resetting the production guard.
        assert call('execute', {'operation': 'vps_virtual-machines_get', 'params': {}})['id'] == 1767265
    call('multi-execute', {'steps': [{'operation': 'vps_virtual-machines_restart', 'params': {}}]}, denied=True)
    assert call('execute', {'operation': 'vps_virtual-machines_get', 'params': {}})['id'] == 1767265
    receipt.update(pass_all=True, denied_operations=forbidden, batch_mutation_denied=True,
                   other_vm_override_ineffective=True, production_writes=0)
    (WORK/'native-runtime-probe-result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
finally:
    shutdown_mcp_servers()
