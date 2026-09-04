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
REQUIRED_MEMBERS = {'1055570806945620030', '1496296175014252634', '1508864261504630925', '344196393512075265'}
STATE = Path('/root/mgs-agent/work/minibot-full-access-smoke-20260904/nicolas-thread-publication.json')

MESSAGES = [
    """<@1055570806945620030> **Atualização 1/5 — minibot Full Access**

Rodolfo pediu para consolidar aqui tudo que foi validado sobre o app `minibot` (`1299247318762949`).

**Estado atual**
- Tech Provider: aprovado.
- Marketing API Access Tier: **Full Access**.
- Prova no runtime: `ads_api_access_tier=standard_access`.
- Permissões centrais em Advanced Access: `ads_management`, `ads_read`, `business_management`, `pages_show_list`, `pages_read_engagement`, `pages_manage_ads`, `pages_manage_metadata` e `pages_messaging`.
- `instagram_basic`: submetida e aguardando aprovação; não altera quota ou velocidade.

**Validação independente**
- Tokens de Roosevelt, Rafael e Carla válidos e vinculados ao app correto.
- CPV13, CPV05 e Eggbev responderam HTTP 200 com `standard_access`.
- 14/14 smokes read-only/dry-run passaram.
- 13 jobs Hermes e o monitor root Eggbev estão verdes.
- Nesta validação: **0 Meta writes, 0 campanhas ativas alteradas e 0 budget alterado**.""",
    """**Atualização 2/5 — o que realmente mudou no rate limit**

A explicação oficial da Meta combina conta e app:

- o consumo principal é separado por conta de anúncios;
- porém a quota é calculada por combinação **conta + aplicativo**;
- o tier do app define o tamanho da quota de cada conta.

**Antes — Limited / `development_access`**
- máximo: 60 pontos;
- decay: 300 segundos;
- ao atingir o máximo: bloqueio de 300 segundos.

**Agora — Full / `standard_access`**
- máximo: 9.000 pontos;
- decay: 300 segundos;
- ao atingir o máximo: bloqueio de 60 segundos.

Isso representa **150× mais capacidade de score**. O amigo do Rodolfo estava certo ao dizer que uma conta pode bater o próprio limite e outra continuar; estava incompleto ao dizer que o app não interfere. O bucket é por conta/app, e foi o Full Access do app que aumentou cada bucket de 60 para 9.000.

Subir campanhas serialmente entre contas continua ajudando, mas não substitui o Full Access.""",
    """**Atualização 3/5 — velocidade antes e agora**

O principal ganho não é um GET isolado ficar 150× mais rápido. O ganho é remover o cooldown de aproximadamente cinco minutos que interrompia os bundles.

Exemplos históricos no tier antigo:
- CPV13, 5 campanhas em 3 bundles: cerca de **23m40s**; até **15m15s** eram cooldowns fixos.
- CPV05, 3 campanhas em 2 bundles: cerca de **14m46s**; até **10m10s** eram cooldowns fixos.

Sem apenas esses cooldowns, as referências ilustrativas seriam aproximadamente 8m25s e 4m36s. Não são promessa: as execuções antigas também tiveram recovery de camadas ausentes.

Benefícios esperados:
- criação e clone em lote mais rápidos;
- readback na mesma execução quando a utilização permitir;
- recovery missing-only mais rápido;
- menos tempo bloqueando Diário, Intraday e monitores.

Continuam existindo: 100 mutations/s por combinação app+conta, limite de edição do mesmo objeto, CPU/tempo, revisão Meta, restrições de Page e validações de payload.""",
    """**Atualização 4/5 — há algo mais para aprovar?**

Para aumentar throughput, **não**. Full Access é o nível máximo relevante. As permissões Advanced ampliam usuários/ativos autorizáveis, mas não aumentam o teto de 9.000.

Rodolfo confirmou que o token do `minibot` está conectado ao wrapper Smart Bidding, que consulta diariamente o investimento das contas. Portanto, o requisito de manutenção — 500 chamadas bem-sucedidas em 15 dias e erro abaixo de 15% nas últimas 500 — está coberto pelo tráfego normal; não criaremos chamadas artificiais.

**Facebook Login for Business**
- arquitetura opcional de onboarding e emissão de tokens;
- não é necessária para os User Access Tokens atuais;
- não aumenta velocidade ou quota.

**`appsecret_proof`**
- não é permissão e não passa por App Review;
- é um HMAC-SHA256 para proteger chamadas server-side;
- melhora segurança, não velocidade;
- não ativar `Require App Secret` antes de todos os consumidores suportarem o parâmetro, ou as chamadas atuais podem falhar.""",
    """**Atualização 5/5 — gates atuais e fontes**

Nenhum canário real de escrita foi executado. O Engine passou nos planos e simulações de `from_zero_prestaged`, `pure_clone` e `clone_prestaged`, inclusive `COMPLETE_PAUSED`, mas o teste real precisa de escopo separado e exato.

O recovery antigo `pg_8348` não será misturado com a validação do Full Access:
- C004/C005 permanecem `PAUSED`, USD45, sem conjuntos/anúncios;
- C006 permanece ausente;
- a lease permanece bloqueada;
- nada muda sem autorização explícita do Rodolfo.

**Conclusão operacional:** o app está completo para throughput; o próximo ganho real vem de um canário Meta `PAUSED` autorizado e da medição do Engine, não de outra permissão.

Fontes oficiais Meta:
- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting/
- https://developers.facebook.com/docs/marketing-api/get-started/authorization/
- https://developers.facebook.com/docs/permissions/
- https://developers.facebook.com/docs/graph-api/guides/secure-requests/

**Próximo passo pendente:** manter zero writes até um pedido separado para o canário ou para o encerramento de `pg_8348`.""",
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
    req = urllib.request.Request(
        'https://discord.com/api/v10' + path,
        data=data,
        method=method,
        headers={
            'Authorization': 'Bot ' + token,
            'Content-Type': 'application/json',
            'User-Agent': 'MGS-Ares/1.0',
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status, json.loads(response.read() or b'{}')


def main() -> int:
    for index, message in enumerate(MESSAGES, 1):
        if len(message) >= 1900:
            raise RuntimeError(f'message {index} length {len(message)} exceeds safe limit')
        if message.count('```') % 2:
            raise RuntimeError(f'message {index} has unbalanced fences')

    load_env(Path('/root/.hermes/profiles/ares/.env'))
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('Ares Discord token unavailable')

    status, me = api('GET', '/users/@me', token)
    if status != 200 or str(me.get('id')) != ARES_ID:
        raise RuntimeError('Discord identity mismatch')
    status, channel = api('GET', f'/channels/{THREAD_ID}', token)
    if status != 200 or str(channel.get('id')) != THREAD_ID or channel.get('thread_metadata', {}).get('archived'):
        raise RuntimeError('Target thread unavailable or archived')
    status, members = api('GET', f'/channels/{THREAD_ID}/thread-members?with_member=true&limit=100', token)
    member_ids = {str(row.get('user_id')) for row in members}
    if status != 200 or not REQUIRED_MEMBERS.issubset(member_ids):
        raise RuntimeError('Required thread participants missing')

    if STATE.exists():
        saved = json.loads(STATE.read_text())
    else:
        saved = {'thread_id': THREAD_ID, 'messages': []}

    for index, content in enumerate(MESSAGES, 1):
        prior = next((row for row in saved['messages'] if row.get('index') == index), None)
        if prior:
            status, existing = api('GET', f'/channels/{THREAD_ID}/messages/{prior["message_id"]}', token)
            if status != 200 or existing.get('content') != content:
                raise RuntimeError(f'existing message {index} failed readback')
            continue
        status, posted = api('POST', f'/channels/{THREAD_ID}/messages', token, {'content': content, 'allowed_mentions': {'parse': [], 'users': ['1055570806945620030'] if index == 1 else []}})
        if status not in {200, 201} or str(posted.get('channel_id')) != THREAD_ID or str(posted.get('author', {}).get('id')) != ARES_ID:
            raise RuntimeError(f'post failed at part {index}')
        row = {'index': index, 'message_id': str(posted.get('id')), 'length': len(content)}
        saved['messages'].append(row)
        STATE.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
        time.sleep(0.4)

    readbacks = []
    for row, expected in zip(sorted(saved['messages'], key=lambda value: value['index']), MESSAGES):
        status, existing = api('GET', f'/channels/{THREAD_ID}/messages/{row["message_id"]}', token)
        readbacks.append({
            'index': row['index'],
            'message_id': row['message_id'],
            'http': status,
            'channel_match': str(existing.get('channel_id')) == THREAD_ID,
            'author_match': str(existing.get('author', {}).get('id')) == ARES_ID,
            'content_match': existing.get('content') == expected,
        })
    saved.update({
        'status': 'complete',
        'channel_name': channel.get('name'),
        'parent_id': channel.get('parent_id'),
        'required_members_present': True,
        'readbacks': readbacks,
        'all_readbacks_ok': all(row['http'] == 200 and row['channel_match'] and row['author_match'] and row['content_match'] for row in readbacks),
    })
    STATE.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'status': saved['status'],
        'thread_id': THREAD_ID,
        'parts': len(saved['messages']),
        'lengths': [row['length'] for row in sorted(saved['messages'], key=lambda value: value['index'])],
        'message_ids': [row['message_id'] for row in sorted(saved['messages'], key=lambda value: value['index'])],
        'required_members_present': saved['required_members_present'],
        'all_readbacks_ok': saved['all_readbacks_ok'],
    }, ensure_ascii=False))
    return 0 if saved['all_readbacks_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
