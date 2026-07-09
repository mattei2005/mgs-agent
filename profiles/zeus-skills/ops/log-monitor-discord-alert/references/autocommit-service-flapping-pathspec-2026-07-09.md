# Auto-commit service flapping por pathspec volátil (2026-07-09)

## Sintoma

Canal de VPS health alterna alerta vermelho e resolução verde para `mgs-autocommit` a cada poucos minutos:

- `mgs-autocommit: active=activating enabled=enabled`
- Logo depois resolução verde, depois novo alerta.

Isso não significa necessariamente falha de push GitHub. Significa que o **service systemd do watcher** está reiniciando/flapping e o monitor de VPS está correto ao detectar `active != active` durante a janela.

## Causa validada

`auto-commit-watcher.sh` estava parseando `git status --porcelain` com `awk '{print $2}'` e rodando `git add -A -- "$path"` por path individual.

Falhas observadas:

1. Path com espaço vinha citado pelo Git (`"work/.../Fase 1 ...tsv"`) e era quebrado como `"work/.../Fase`.
2. Deleção já staged (`D  data/utility-canary-loop.paused`) não existe mais no working tree/index; `git add -A -- data/utility-canary-loop.paused` retorna `fatal: pathspec ... did not match any files`.
3. Com `set -euo pipefail`, qualquer `git add` fatal derruba o watcher; systemd reinicia; VPS health alerta/resolve em loop.

## Correção canônica

No watcher:

1. Capturar status com `git status --porcelain=v1 -z` em arquivo temporário — não guardar NUL em variável Bash.
2. Parsear o arquivo com Python, preservando status de 2 caracteres + path.
3. Para mensagem/guardrail, usar só o path parseado, não `awk` no porcelain bruto.
4. No staging:
   - `D ` staged deletion: **skip**; já está staged.
   - ` ?D` unstaged deletion: `git add -u -- "$path"`.
   - demais: `git add -A -- "$path"`.
   - qualquer path volátil que falhar deve logar `WARN` e continuar, não matar o service.

## Validação esperada

```bash
bash -n /root/mgs-agent/scripts/auto-commit-watcher.sh
systemctl restart mgs-autocommit.service
sleep 45
systemctl show mgs-autocommit.service -p ActiveState -p SubState -p NRestarts --no-pager
journalctl -u mgs-autocommit --since 'YYYY-MM-DD HH:MM:SS' --no-pager -n 40
```

Resultado esperado:

- `ActiveState=active`
- `SubState=running`
- `NRestarts=0` após restart limpo
- Sem `fatal: pathspec` novo no journal
- Próxima execução do `monitor-vps-health.py` limpa `alerts.service_mgs-autocommit` e para o vermelho/verde recorrente.

## Regra operacional

Quando alerta vermelho/verde de service incomodar por flapping, não silenciar o monitor primeiro. Investigar `journalctl -u <service>` e corrigir a causa do restart loop. Só ajustar debounce/threshold se o service estiver saudável e o alerta for realmente falso positivo.
