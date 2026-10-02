#!/usr/bin/env python3
"""Read-only Hostinger VPS MCP probe, reusable by diagnostics and scheduled callers."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

import os

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ModuleNotFoundError:
    # Keep cron callers stable across Hermes worktree/venv cutovers.
    python = Path('/root/.local/bin/hermes').resolve().parent / 'python'
    if python.is_file() and python.resolve() != Path(sys.executable).resolve():
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
    raise RuntimeError('MCP SDK unavailable in active Hermes runtime')


async def probe(verify_guards=False):
    params = StdioServerParameters(command='/usr/bin/python3', args=['/root/mgs-agent/scripts/hostinger-vps-mcp-launch.py'])
    now = datetime.now(timezone.utc)
    with tempfile.TemporaryFile(mode='w+', dir='/root/.hermes/profiles/zeus/cache/scratch') as errors:
        async with stdio_client(params, errlog=errors) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert names == {'search', 'execute', 'multi-execute'}
                assert all(tool.annotations.read_only_hint for tool in tools.tools)
                result = {'observed_at': now.isoformat(), 'mcp_tools': sorted(names), 'guarded_get_only': True, 'financial_writes': 0}
                search = await session.call_tool('search', {'query': 'vps', 'limit': 5})
                assert not search.is_error
                text = '\n'.join(x.text for x in search.content if x.type == 'text')
                assert 'vps_virtual-machines_get' in text and 'vps_backups_list' in text
                assert 'vps_virtual-machines_restart' not in text and 'vps_firewall_create' not in text
                for operation in ['vps_virtual-machines_get', 'vps_backups_list', 'vps_snapshots_get', 'vps_actions_list', 'vps_virtual-machines_metrics']:
                    args = {}
                    if operation.endswith('_metrics'):
                        args = {'date_from': (now-timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'), 'date_to': now.strftime('%Y-%m-%dT%H:%M:%SZ')}
                    reply = await session.call_tool('execute', {'operation': operation, 'params': args})
                    txt = '\n'.join(x.text for x in reply.content if x.type == 'text')
                    if reply.is_error:
                        # Do not log provider payloads containing credential-bearing URLs.
                        raise RuntimeError(f'{operation} failed: {txt[:100] if "HTTP " in txt else "MCP error"}')
                    value = json.loads(txt)
                    if operation.endswith('_get') and 'virtual-machines' in operation:
                        assert value['id'] == 1767265 and value['hostname'] == 'srv1767265.hstgr.cloud'
                        result['vps'] = {key: value.get(key) for key in ['id', 'hostname', 'state']}
                    else:
                        if isinstance(value, list):
                            result[operation] = {'pass': True, 'count': len(value)}
                        elif isinstance(value, dict):
                            safe = {'pass': True, 'keys': sorted(value.keys())}
                            if isinstance(value.get('data'), list):
                                safe['count'] = len(value['data'])
                            result[operation] = safe
                        else:
                            result[operation] = {'pass': True, 'kind': type(value).__name__}
                if verify_guards:
                    blocked = []
                    for operation in ['vps_virtual-machines_restart', 'vps_virtual-machines_stop', 'vps_backups_restore', 'vps_firewall_create', 'billing_orders_create']:
                        reply = await session.call_tool('execute', {'operation': operation, 'params': {}})
                        assert reply.is_error, f'Forbidden operation accepted: {operation}'
                        blocked.append(operation)
                    reply = await session.call_tool('multi-execute', {'steps': [{'operation': 'vps_virtual-machines_restart', 'params': {}}]})
                    assert reply.is_error
                    # A caller-supplied different ID cannot change the concretized API URL.
                    reply = await session.call_tool('execute', {'operation': 'vps_virtual-machines_get', 'params': {'virtualMachineId': 1}})
                    assert not reply.is_error
                    assert json.loads(reply.content[0].text)['id'] == 1767265
                    result['denied_operations'] = blocked
                    result['batch_mutation_denied'] = True
                    result['other_vm_override_ineffective'] = True
                result['pass'] = True
                return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-guards', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = asyncio.run(probe(args.verify_guards))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
