#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

THREAD_ID = '1545558483812884581'
ARES_ID = '1508864261504630925'
STATE = Path('/root/mgs-agent/work/minibot-full-access-smoke-20260904/nicolas-thread-publication.json')

REPLACEMENTS = [
    """<@1055570806945620030> **Atualização 1/5 — upgrade do app concluído**

Nicolas, o aplicativo `minibot`, usado pelo Ares nas operações da Meta, recebeu o upgrade de **Full Access**.

Antes ele operava no nível de desenvolvimento, adequado para testes e com uma capacidade muito pequena para campanhas em lote. Agora está no nível liberado pela Meta para uma operação de produção com muito mais volume.

A atualização já foi confirmada nas operações de CPV13, CPV05 e Eggbev.

Importante: essa mudança foi somente no aplicativo. Durante a validação, nenhuma campanha ativa, orçamento ou configuração das campanhas foi alterada.""",
    """**Atualização 2/5 — como funcionava antes**

Antes do upgrade, cada bloco de duas campanhas praticamente ocupava toda a capacidade disponível naquele momento.

Depois de subir o bloco, o Ares precisava aguardar aproximadamente cinco minutos para conferir o resultado e continuar para o próximo. Em pedidos maiores, essas pausas se acumulavam.

Exemplos reais do funcionamento anterior:
- cinco campanhas chegaram a levar aproximadamente **23 minutos e 40 segundos**;
- três campanhas chegaram a levar aproximadamente **14 minutos e 46 segundos**.

A maior parte desse atraso não era criação dos anúncios em si: era o tempo obrigatório de espera entre os blocos.""",
    """**Atualização 3/5 — como ficou agora**

Com o Full Access, a capacidade disponível aumentou muito e aquela espera fixa de aproximadamente cinco minutos entre blocos deixa de ser necessária quando a Meta estiver respondendo normalmente.

Na prática, o Ares pode:
- avançar para o próximo bloco mais rapidamente;
- conferir as campanhas na mesma execução;
- concluir lotes maiores com menos interrupções;
- recuperar uma etapa incompleta sem esperar vários ciclos apenas para fazer a conferência.

Usando os tempos antigos somente como referência, o lote de cinco campanhas poderia cair de cerca de 23m40s para algo próximo de 8m25s, e o de três campanhas de 14m46s para perto de 4m36s. Esses números são estimativas; o tempo real será medido no primeiro teste autorizado.""",
    """**Atualização 4/5 — benefícios para a operação**

Os principais benefícios são:

- **criação e clonagem mais rápidas**, principalmente em pedidos com várias campanhas;
- **menos pausas no meio da execução**;
- **conferência final mais rápida** depois da criação;
- **recuperação de falhas mais ágil**, sem repetir etapas já concluídas;
- **menos chance de uma criação atrasar os relatórios e monitores**;
- **mais capacidade para trabalhar com várias contas**, mantendo cada conta organizada separadamente.

O upgrade melhora capacidade e velocidade, mas não elimina o tempo normal da própria Meta para processar vídeos, revisar anúncios ou aprovar campanhas.""",
    """**Atualização 5/5 — conclusão**

O aplicativo está agora no melhor nível disponível para a velocidade das operações que fazemos.

Não existe outro upgrade de acesso que aumente ainda mais essa capacidade neste caso. A partir daqui, os próximos ganhos virão da medição real e dos ajustes no modo como o Ares organiza os lotes.

Resumo simples:

**Antes:** capacidade pequena, blocos de duas campanhas e esperas acumuladas de aproximadamente cinco minutos.

**Agora:** capacidade muito maior, continuidade entre os blocos e possibilidade de concluir lotes e conferências em bem menos tempo.

Nenhum teste real de criação foi feito nesta atualização. O primeiro teste será uma campanha pausada, em um pedido separado e autorizado, sem interferir nas campanhas que já estão rodando.""",
]


def load_env(path: Path) -> None:
    for raw in path.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    for attempt in range(1, 6):
        request = urllib.request.Request(
            'https://discord.com/api/v10' + path,
            data=data,
            method=method,
            headers={
                'Authorization': 'Bot ' + token,
                'Content-Type': 'application/json',
                'User-Agent': 'MGS-Ares/1.0',
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read() or b'{}')
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 5:
                raise
            try:
                body = json.loads(exc.read() or b'{}')
            except (TypeError, ValueError, json.JSONDecodeError):
                body = {}
            retry_after = float(body.get('retry_after') or exc.headers.get('Retry-After') or 1.0)
            time.sleep(min(max(retry_after, 0.25), 30.0) + 0.15)
    raise RuntimeError('Discord API retry loop exhausted')


def main() -> int:
    for index, content in enumerate(REPLACEMENTS, 1):
        if len(content) >= 1900:
            raise RuntimeError(f'part {index} exceeds safe Discord length')
        if content.count('```') % 2:
            raise RuntimeError(f'part {index} has unbalanced fences')

    saved = json.loads(STATE.read_text())
    rows = sorted(saved.get('messages') or [], key=lambda row: row['index'])
    if len(rows) != len(REPLACEMENTS):
        raise RuntimeError('publication state does not contain exactly five messages')

    load_env(Path('/root/.hermes/profiles/ares/.env'))
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('Ares Discord token unavailable')

    preread = []
    for row in rows:
        status, current = api('GET', f'/channels/{THREAD_ID}/messages/{row["message_id"]}', token)
        index = row['index']
        expected_prefix = f'**Atualização {index}/5'
        content = str(current.get('content') or '')
        prefix_ok = expected_prefix in content[:100]
        if status != 200 or str(current.get('channel_id')) != THREAD_ID or str(current.get('author', {}).get('id')) != ARES_ID or not prefix_ok:
            raise RuntimeError(f'pre-read mismatch at part {index}')
        preread.append({'index': index, 'message_id': row['message_id'], 'http': status, 'prefix_ok': prefix_ok})

    updated = []
    for row, replacement in zip(rows, REPLACEMENTS):
        status, current = api('GET', f'/channels/{THREAD_ID}/messages/{row["message_id"]}', token)
        if current.get('content') == replacement:
            updated.append({'index': row['index'], 'message_id': row['message_id'], 'status': 'already_current'})
            continue
        status, edited = api(
            'PATCH',
            f'/channels/{THREAD_ID}/messages/{row["message_id"]}',
            token,
            {'content': replacement, 'allowed_mentions': {'parse': []}},
        )
        if status != 200 or str(edited.get('id')) != row['message_id'] or str(edited.get('author', {}).get('id')) != ARES_ID:
            raise RuntimeError(f'edit failed at part {row["index"]}')
        updated.append({'index': row['index'], 'message_id': row['message_id'], 'status': 'edited'})

    readbacks = []
    for row, expected in zip(rows, REPLACEMENTS):
        status, current = api('GET', f'/channels/{THREAD_ID}/messages/{row["message_id"]}', token)
        readbacks.append({
            'index': row['index'],
            'message_id': row['message_id'],
            'http': status,
            'channel_match': str(current.get('channel_id')) == THREAD_ID,
            'author_match': str(current.get('author', {}).get('id')) == ARES_ID,
            'content_match': current.get('content') == expected,
        })

    result = {
        'status': 'revised_nontechnical',
        'thread_id': THREAD_ID,
        'preread': preread,
        'updates': updated,
        'lengths': [len(content) for content in REPLACEMENTS],
        'readbacks': readbacks,
        'all_readbacks_ok': all(
            row['http'] == 200 and row['channel_match'] and row['author_match'] and row['content_match']
            for row in readbacks
        ),
    }
    saved['revision'] = result
    STATE.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'status': result['status'],
        'parts': len(rows),
        'edited': sum(row['status'] == 'edited' for row in updated),
        'lengths': result['lengths'],
        'all_readbacks_ok': result['all_readbacks_ok'],
    }, ensure_ascii=False))
    return 0 if result['all_readbacks_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
