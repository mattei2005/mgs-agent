#!/usr/bin/env python3
"""Scoped Ares SHEIN report routing; dry-run by default, native config writer."""
import argparse
import asyncio
import copy
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path('/root/mgs-agent')
PROFILE = Path('/root/.hermes/profiles/ares')
STRUCTURE = ROOT / 'data/discord-shein-report-channel-structure.json'
STATE = ROOT / 'data/discord-shein-report-gateway-routing.json'
AUTHORITY = '1558252008467734678'
SOURCE = '1557274000680288307'
BOT = '1508864261504630925'

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def repo_path():
    return Path('/root/.local/bin/hermes').resolve().parents[2]

def load_plan():
    import yaml
    before = yaml.safe_load((PROFILE / 'config.yaml').read_text())
    after = copy.deepcopy(before)
    structure = json.loads(STRUCTURE.read_text())
    accounts = json.loads((ROOT / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json').read_text())['accounts']
    groups = structure['groups']
    assert len(groups) == 6 and sum(len(g['threads']) for g in groups) == 36
    routes = []
    discord_cfg = after['discord']
    for key in ('allowed_channels', 'free_response_channels'):
        value = discord_cfg[key]
        assert isinstance(value, str), (key, type(value).__name__)
        ids = value.split(',')
        for g in groups:
            if g['channel_id'] not in ids:
                ids.append(g['channel_id'])
        discord_cfg[key] = ','.join(ids)
    for g in groups:
        cid = g['channel_id']
        discord_cfg.setdefault('thread_auto_add_users_by_channel', {})[cid] = [u for u in g['participants'] if u != BOT]
        discord_cfg.setdefault('channel_prompts', {})[cid] = (
            f"INSTRUCAO Ares SHEIN {g['code'].upper()} — Relatorios e Intraday\n"
            f"Canal de relatorios, gestor {g['manager']}, origem Campaign Ops {g['source_channel_id']}. "
            "Ares e o agente responsavel por responder aos humanos autorizados sem exigir @mention. "
            "Use a conta exata vinculada a cada thread, sem misturar gestores. "
            "Configuracao de relatorio depende da instrucao humana vigente, nao nasce da existencia da thread. "
            "Responder na thread atual; nao sobrescrever titulo manual. "
            "Esta rota nao ativa cron, redireciona envios automaticos nem autoriza writes em campanhas. "
            "Pedidos de Campaign Ops devem seguir a origem e o contrato vigentes, sem nova delegacao inferida."
        )
        for t in g['threads']:
            m = re.fullmatch(r'📈(.+) Conta (\d+) Intraday', t['report_thread_name'])
            assert m, t['report_thread_name']
            site, number = m.groups()
            matches = [a for a in accounts if a['manager_code'].lower() == g['code'] and a['channel_id'] == g['source_channel_id'] and a['name'].startswith(site + '-US-SHEIN-') and a['name'].endswith('-' + number + '-' + g['code'].upper())]
            assert len(matches) == 1, (t['report_thread_id'], len(matches))
            account = matches[0]
            route = dict(thread_id=t['report_thread_id'], channel_id=cid, source_channel_id=g['source_channel_id'], source_thread_id=t['source_thread_id'], manager_code=g['code'].upper(), account_id=account['account_id'], account_name=account['name'])
            routes.append(route)
            discord_cfg['channel_prompts'][route['thread_id']] = (
                f"INSTRUCAO Ares — SHEIN Intraday {account['name']}\n"
                f"Conta desta thread: {account['name']}, account_id={account['account_id']}, moeda={account['currency']}, fuso={account['timezone_name']}. "
                f"Gestor {g['manager']} ({g['code'].upper()}); canal de relatorios {cid}; origem Campaign Ops {g['source_channel_id']}, thread de criacao {t['source_thread_id']}. "
                "Responder aqui aos humanos autorizados sem exigir @mention. Preservar o titulo manual. "
                "Use o catalogo canonico SHEIN-US-DIRECT-accounts.json e a configuracao vigente desta conta; nao herdar regras de outra operacao. "
                "Carregar meta-ads-intraday-operations somente quando o pedido exigir definicao ou operacao do relatorio. "
                "Esta thread e de relatorios/configuracao Intraday sob demanda: sua existencia nao configura nem ativa automacao recorrente, nao muda destino dos envios e nao autoriza writes Meta. "
                "Quando Rodolfo disser que vai elaborar as regras, reconhecer e aguardar o detalhamento; nao inventar configuracao. "
                "Campanhas continuam sob Ares no canal operacional de origem e nos gates existentes."
            )
    assert len({r['thread_id'] for r in routes}) == 36
    assert before['discord']['allow_from'] == after['discord']['allow_from']
    assert before['discord']['require_mention'] == after['discord']['require_mention'] is True
    assert before['discord']['thread_require_mention'] == after['discord']['thread_require_mention'] is True
    return before, after, routes

def gate_test(cfg, routes):
    sys.path.insert(0, str(repo_path()))
    import discord
    from plugins.platforms.discord.adapter import DiscordAdapter
    # Dynamic fixture deliberately replaces network-bound instance members.
    from typing import Any
    adapter: Any = object.__new__(DiscordAdapter)
    adapter.platform = SimpleNamespace(value='discord')
    adapter.config = SimpleNamespace(extra=cfg['discord'])
    # Isolate fixture from process-wide YAML->env bridge and the caller profile.
    adapter._gate_env_snapshot = {'DISCORD_ALLOWED_CHANNELS': '', 'DISCORD_IGNORED_CHANNELS': '', 'DISCORD_NO_THREAD_CHANNELS': '', 'DISCORD_FREE_RESPONSE_CHANNELS': ''}
    adapter._client = SimpleNamespace(user=SimpleNamespace(id=int(BOT), bot=True))
    adapter._voice_text_channels = {}
    adapter._threads = set()
    adapter._get_parent_channel_id = lambda ch: str(ch.parent_id)
    adapter._format_thread_chat_name = lambda ch: 'SHEIN routing smoke'
    adapter._get_effective_topic = lambda *args, **kwargs: ''
    class ReachedSource(Exception):
        pass
    def source(**kwargs):
        raise ReachedSource()
    adapter.build_source = source
    async def run(route, mention=False):
        ch = Mock(spec=discord.Thread)
        ch.id = int(route['thread_id'])
        ch.parent_id = int(route['channel_id'])
        ch.name = 'report-smoke'
        ch.parent = SimpleNamespace(name='report-parent')
        ch.guild = SimpleNamespace(id=1185714635991679006, name='MGS')
        msg = SimpleNamespace(channel=ch, id=123, content=(f'<@{BOT}> ' if mention else '') + 'teste sem efeitos', mentions=[], attachments=[], reference=None, guild=ch.guild, author=SimpleNamespace(id=344196393512075265, display_name='Rodolfo', bot=False), type=discord.MessageType.default)
        try:
            await adapter._handle_message(msg)
        except ReachedSource:
            return True
        return False
    async def checks():
        passed = 0
        for route in routes:
            assert await run(route), route['thread_id']
            passed += 1
        unknown = dict(thread_id='999999999999999999', channel_id='999999999999999998')
        assert not await run(unknown, mention=True), 'unknown channel admitted'
        visitor = dict(thread_id='999999999999999997', channel_id='1496267442899521627')
        assert not await run(visitor), 'Zeus channel mention gate widened'
        assert await run(visitor, mention=True), 'explicit authorized visitor mention lost'
        return passed
    return {'mentionless_thread_gate_tests': asyncio.run(checks()), 'unknown_channel_rejected': True, 'zeus_mention_gate_preserved': True, 'account_routes': len(routes)}

def audit(event, **data):
    with (ROOT / 'logs/events-audit.jsonl').open('a') as f:
        f.write(json.dumps(dict(ts=now(), agent='zeus', event=event, authority_message_id=AUTHORITY, source_thread_id=SOURCE, **data), ensure_ascii=False) + '\n')

def save_json(path, data):
    tmp = path.with_suffix(path.suffix + '.routing-tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)

def update_inventory(status, evidence):
    p = ROOT / 'data/infra-inventory.json'
    with (ROOT / 'data/.infra-inventory.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        d = json.loads(p.read_text())
        rows = d.setdefault('runtime_artifacts', [])
        rid = 'SHEIN-REPORT-GATEWAY-' + AUTHORITY
        entry = dict(id=rid, agent='zeus', authority_message_id=AUTHORITY, source_thread_id=SOURCE, path=str(STATE), paths=[str(PROFILE / 'config.yaml'), str(ROOT / 'profiles/ares-config.yaml'), str(Path(__file__).resolve()), str(ROOT / 'scripts/mgs-shein-report-routing-closure.py')], purpose='Scoped Ares response routing for six SHEIN report channels and 36 Intraday threads; no campaign/cron/credential/whitelist change', status=status, updated_at=now(), validation=evidence)
        existing = next((r for r in rows if r.get('id') == rid), None)
        if existing is None:
            rows.append(entry)
        else:
            existing.update(entry)
        save_json(p, d)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    before, after, routes = load_plan()
    evidence = gate_test(after, routes)
    if args.apply:
        sys.path.insert(0, str(repo_path()))
        from hermes_cli.config import atomic_config_write
        backup = ROOT / 'backups' / ('shein-report-routing-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(PROFILE / 'config.yaml', backup / 'ares-config.yaml')
        mirror = ROOT / 'profiles/ares-config.yaml'
        if mirror.exists():
            shutil.copy2(mirror, backup / 'ares-config-mirror.yaml')
        atomic_config_write(PROFILE / 'config.yaml', after)
        shutil.copy2(PROFILE / 'config.yaml', mirror)
        import yaml
        actual = yaml.safe_load((PROFILE / 'config.yaml').read_text())
        assert actual == after
        assert mirror.read_bytes() == (PROFILE / 'config.yaml').read_bytes()
        state = dict(authority_message_id=AUTHORITY, source_thread_id=SOURCE, status='configured_restart_pending', configured_at=now(), backup=str(backup), channels=sorted({r['channel_id'] for r in routes}), routes=routes, validation=evidence, original_silent_message_id='1558251056868102207', original_silent_thread_id='1558146725376557126', no_campaign_writes=True, no_recurring_automation_changes=True)
        save_json(STATE, state)
        update_inventory(state['status'], evidence)
        audit('shein_report_gateway_routing_configured', channels=state['channels'], threads=len(routes), evidence=evidence, backup=str(backup))
        print(json.dumps(dict(status=state['status'], **evidence)))
    elif args.verify:
        assert before == after, 'config missing intended route entries'
        assert (ROOT / 'profiles/ares-config.yaml').read_bytes() == (PROFILE / 'config.yaml').read_bytes()
        print(json.dumps(dict(status='config_and_real_adapter_gate_verified', **evidence)))
    else:
        print(json.dumps(dict(status='dry_run_pass', **evidence)))

if __name__ == '__main__':
    main()
