# Discord live tool-call trace com cleanup automático

## Quando usar

Rodolfo quer a UX de “atividade ao vivo” no Discord: o agente mostra chamadas de ferramenta (`search_files`, `read_file`, `execute_code`, `terminal`, etc.) enquanto trabalha, mas remove esses breadcrumbs quando a resposta final chega com sucesso.

## Diagnóstico prévio

1. Confirmar que o runtime Hermes já tem suporte genérico a `display.cleanup_progress` em `gateway/run.py` e resolução em `gateway/display_config.py`.
2. Confirmar se o adapter Discord implementa `delete_message`. Sem isso, o runner desativa cleanup silenciosamente porque compara `type(adapter).delete_message` com `BasePlatformAdapter.delete_message`.
3. Verificar configs atuais dos profiles:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
for profile in ['zeus','atena','ares']:
    p=Path(f'/root/.hermes/profiles/{profile}/config.yaml')
    c=yaml.safe_load(p.read_text()) or {}
    print(profile, ((c.get('display') or {}).get('platforms') or {}).get('discord'))
PY
```

## Patch runtime necessário

Adicionar `DiscordAdapter.delete_message(...)` ao plugin Discord (`/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py`) usando `channel.fetch_message(message_id)` + `msg.delete()` e retornando `SendResult`.

Patch durável MGS:

```text
/root/mgs-agent/patches/hermes/discord-live-tool-trace-cleanup.patch
```

## Config por profile

Ativar em `display.platforms.discord`:

```yaml
display:
  platforms:
    discord:
      tool_progress: all
      tool_preview_length: 80
      cleanup_progress: true
      interim_assistant_messages: false
      long_running_notifications: true
      busy_ack_detail: false
```

Aplicar tanto nos profiles ativos:

```text
/root/.hermes/profiles/{zeus,atena,ares}/config.yaml
```

quanto nas cópias versionadas:

```text
/root/mgs-agent/profiles/{zeus,atena,ares}-config.yaml
```

## Validação sem restart

```bash
cd /root/.hermes/hermes-agent
python3 -m py_compile plugins/platforms/discord/adapter.py gateway/run.py gateway/display_config.py
python3 - <<'PY'
import ast, yaml
from pathlib import Path
p='/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py'
tree=ast.parse(open(p).read())
for cls in [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=='DiscordAdapter']:
    methods={n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert 'delete_message' in methods
for profile in ['zeus','atena','ares']:
    p=Path(f'/root/.hermes/profiles/{profile}/config.yaml')
    c=yaml.safe_load(p.read_text()) or {}
    d=((c.get('display') or {}).get('platforms') or {}).get('discord') or {}
    assert d.get('tool_progress') == 'all'
    assert d.get('cleanup_progress') is True
    assert d.get('tool_preview_length') == 80
print('live tool trace config ok')
PY
```

Também registrar PIDs antes/depois para provar que não houve restart quando Rodolfo pediu apenas aplicação/preparação.

## Ativação

Config/patch só entram em produção após restart dos gateways afetados. Para MGS, tratar como mudança de serviço ativo: reportar validação e pedir autorização separada para restart controlado de `zeus-gateway`, `atena-gateway` e `ares-gateway`.

## Pitfalls

- `display.tool_progress: off` global não impede override específico em `display.platforms.discord`; o override por plataforma vence.
- `cleanup_progress` só remove breadcrumbs em execuções bem-sucedidas. Runs com falha mantêm os breadcrumbs como trilha de debug.
- Se `delete_message` não existir no adapter Discord, a config `cleanup_progress: true` não terá efeito prático.
- Não confundir com `ephemeral_system_ttl`; esse TTL apaga mensagens de sistema após tempo fixo, não o lifecycle “some quando termina”.
- Não reiniciar no mesmo turno se o pedido foi apenas preparar/aplicar sem autorização explícita para restart.
