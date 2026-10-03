"""Origin-thread readback for isolated Zeus learning, not an infra incident.
One daily bot-owned learning embed per thread, updated with verified paths.
"""
from __future__ import annotations
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from mgs_alert_transport import request, post_verified


def origin_channel(receipt, profiles_root):
    session = receipt.get('session') or {}
    channel = str(session.get('thread_id') or session.get('chat_id') or '')
    if receipt.get('profile') != 'zeus' or receipt.get('subsystem') not in ('skills', 'skill') or session.get('platform') != 'discord' or not channel.isdigit():
        return None
    before, after = receipt.get('before') or {}, receipt.get('after') or {}
    paths = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
    root = Path(profiles_root) / 'zeus' / 'skills'
    if not paths or any(not Path(p).is_relative_to(root) for p in paths):
        return None
    return channel


def publish_learning(receipt, mirror_paths, *, repo_root, profiles_root):
    channel = origin_channel(receipt, profiles_root)
    if not channel:
        raise ValueError('Learning receipt has no verified origin route')
    state_path = Path(repo_root) / 'data/zeus-learning-origin-state.json'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(state_path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, 'r+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        raw = stream.read()
        store = json.loads(raw) if raw else {}
        day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        key = channel + ':' + day
        record = store.setdefault(key, {'paths': [], 'correlations': []})
        correlation = str(receipt.get('correlation_id') or receipt.get('id'))
        paths = sorted(set(record['paths']) | set(mirror_paths))
        root = Path(repo_root) / 'profiles/zeus-skills'
        labels = [str(Path(p).relative_to(root)) if Path(p).is_relative_to(root) else Path(p).name for p in paths]
        summary = '\n'.join('• ' + p for p in labels[:10])
        if len(labels) > 10:
            summary += f'\n+{len(labels)-10} arquivos validados no registro local'
        payload = {'content': '', 'allowed_mentions': {'parse': [], 'users': [], 'roles': [], 'replied_user': False}, 'embeds': [{'title': 'Aprendizados de Zeus — salvos', 'color': 3447003, 'description': 'Subsistema: skills de Zeus. Atualizações de procedimento salvas; leitura do alvo/espelho e inventário confirmados.\n\n' + summary, 'footer': {'text': 'Registro de aprendizado isolado; não é incidente de infraestrutura'}}]}
        def save():
            stream.seek(0); json.dump(store, stream, ensure_ascii=False, indent=2); stream.write('\n'); stream.truncate(); stream.flush(); os.fsync(stream.fileno())
        url = f'https://discord.com/api/v10/channels/{channel}/messages'
        # This helper deliberately uses the actual validated origin channel,
        # not a caller-supplied arbitrary API destination.
        previous = record.get('message_id')
        if previous:
            request('PATCH', url + '/' + previous, payload)
            result = request('GET', url + '/' + previous)
            if result.get('id') != previous or result.get('content', '') or result.get('mentions') or not result.get('embeds') or result['embeds'][0].get('description') != payload['embeds'][0]['description']:
                raise RuntimeError('Learning origin readback failed')
            mid = previous
        else:
            def created(mid):
                record['message_id'] = mid
                save()
            mid = post_verified(payload, channel=channel, on_created=created)
        record.update({'paths': paths, 'message_id': mid, 'updated_at': datetime.now(timezone.utc).isoformat(), 'readback': True})
        if correlation not in record['correlations']:
            record['correlations'].append(correlation)
        save()
        return mid
