# Discord thread auto-archive warning cron

## Quando usar

Quando Rodolfo pedir para ser avisado antes de threads Discord sumirem/ficarem ocultas por inatividade, especialmente threads configuradas com `Hide After Inactivity = 1 Week`.

## Padrão validado

- Monitor diário com keepalive automático quando Rodolfo pedir esse modo.
- Consultar Discord API em `/guilds/{guild_id}/threads/active` usando os bot tokens dos perfis MGS relevantes (`zeus`, `atena`, `ares`, `legacy-agent`).
- Filtrar apenas threads ativas com `thread_metadata.auto_archive_duration == 10080` minutos (7 dias). Threads de 1 dia ficam fora desse monitor.
- Calcular janela de alerta usando `thread_metadata.archive_timestamp` ou `last_message_id` snowflake como fallback, somando 10080 minutos.
- Quando faltar até 24h para auto-archive, postar uma mensagem curta na própria thread: `Mantendo a thread ativa para não arquivar automaticamente.`
- Usar um bot que já enxerga a thread, preferindo o primeiro agente em `AGENTS` presente em `item['agents']`; Zeus é fallback.
- Deduplicar por `thread_id + archive_at` em state file local ignorado pelo git, para não repetir o keepalive no mesmo ciclo.
- Alertar Rodolfo no canal Zeus somente se o keepalive falhar em alguma thread.

## Pitfalls e correções operacionais

### 7 dias desde criação ≠ prazo real de archive

Não calcular deadline de auto-archive pelo snowflake/ID da thread como se fosse criação + 7 dias. Isso é apenas idade da thread e gera falso diagnóstico: threads antigas podem continuar abertas porque receberam atividade posterior.

Para responder “quando essa thread vai arquivar?” ou validar comportamento real:

1. Consultar a thread diretamente via Discord API: `GET /channels/{thread_id}` com token de um bot que tenha acesso.
2. Ler `thread_metadata.archived` e `thread_metadata.auto_archive_duration`.
3. Usar `thread_metadata.archive_timestamp` como sinal de atividade/arquivo quando disponível, e `last_message_id` snowflake como fallback/sinal adicional.
4. Calcular o deadline real a partir da atividade mais recente observável + `auto_archive_duration`.
5. Reportar explicitamente quando uma thread está com `auto_archive_duration=1440` (1 dia) em vez de `10080` (7 dias). Um monitor limitado a 7 dias não protege threads configuradas para 1 dia.

### Gap de cobertura: threads de 1 dia

Se Rodolfo pedir para “não deixar sair/arquivar” threads em geral, não filtrar apenas `auto_archive_duration == 10080`. Primeiro auditar os IDs/canais reais: algumas threads podem estar em `1440` minutos e precisar de keepalive próprio ou alteração de duração.

## Implementação MGS conhecida

Script criado em produção:

- `/root/mgs-agent/scripts/monitor-discord-thread-archive-warnings.py`

Cron root conhecido:

```cron
16 9 * * * flock -n /var/lock/monitor_discord_thread_archive_warnings.lock /root/mgs-agent/scripts/monitor-discord-thread-archive-warnings.py >> /root/mgs-agent/logs/monitor-discord-thread-archive-warnings.log 2>&1
```

State file:

- `/root/mgs-agent/data/discord-thread-archive-warning-state.json`

## Validação mínima

1. `python3 -m py_compile` no script do monitor e nos scripts auxiliares modificados.
2. Dry-run real: `monitor-discord-thread-archive-warnings.py --dry-run --json`.
3. API scan real: confirmar que os quatro perfis conseguem consultar active threads; não imprimir tokens.
4. Verificar `crontab -l` contém o comando com `flock`.
5. Verificar `data/infra-inventory.json` contém o script e a linha de cron.
6. Regenerar `docs/CRONS.md` via `cron-control-plane.py --write-doc` quando o root crontab mudar.

## Pitfall: verificação ad-hoc exigida pelo Hermes

Se o runtime marcar a edição como `Verification status: unverified`, criar um script temporário sob `/tmp` com prefixo `hermes-verify-`, usando caminho seguro, e executar checks focados contra o comportamento alterado. Depois remover o arquivo temporário e reportar explicitamente como:

- `ad-hoc verification, not suite green`

O script ad-hoc deve mockar a janela de alerta de ~23h, validar formatação do alerta, cobertura dos agentes, crontab e inventário. Não chamar isso de suite green.

## Escopo e limites

- Esse monitor só enxerga threads acessíveis aos bots usados.
- Threads já arquivadas não aparecem em `/threads/active`; o objetivo é avisar antes de sumir, não indexar histórico arquivado.
- Não deve enviar keepalive automático sem pedido explícito, porque gera ruído operacional.
