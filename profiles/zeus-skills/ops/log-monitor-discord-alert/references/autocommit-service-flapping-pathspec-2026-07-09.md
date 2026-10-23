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

## Bloqueio pré-commit por nome sensível

- Diferencie rejeição remota de bloqueio local: `BLOQUEADO: arquivo sensível` sem novo `auto-push START` significa que o commit nem começou. Confirme conectividade e SHA remoto com `git ls-remote`; um serviço `active` não prova que o lote foi publicado.
- Para fonte/teste cujo nome contém `private`, reconcilie a autorização de origem, leia integralmente os arquivos e procure credenciais sem imprimir valores. Quando for falso positivo comprovado, acrescente somente exceções de paths exatos, ancoradas, com regressões que mantenham irmãos, prefixo `work/`, `.bak` e arquivos de credenciais bloqueados. Não renomeie código ainda em edição por outra sessão nem amplie por diretório/extensão.
- O watcher carrega o regex apenas no início; editar seu script não atualiza o processo residente. Valide com o mesmo entrypoint e lock exclusivo, opcionalmente usando `MGS_AUTOCOMMIT_BATCH_TARGET=1` em uma única execução limitada, e restaure o serviço com os defaults permanentes. Não use `git add`, commit ou push manual para simular recuperação.
- Antes de restaurar o serviço após uma execução limitada, aguarde o término dos hooks assíncronos: eles podem herdar o FD do flock e fazer a nova instância sair silenciosamente com código zero. Verifique `active/running` e PID não zero novamente após alguns segundos, além de `batch_target=10` no novo startup. Se o serviço sair por lock ainda ocupado, reconcilie o proprietário e inicie novamente somente após liberação; não mate outro writer.
- Exija um novo commit automático, confirmação no log de push, readback do SHA remoto e monitor sem falhas. Push concorrente pode retornar `cannot lock ref` mesmo quando o SHA já chegou ao remoto; reconcilie HEAD/remote e ancestralidade antes de retry, sem push manual ou force. Preserve alterações operacionais concorrentes e não afirme working tree limpo enquanto seus produtores continuam ativos.

## Regra operacional

Quando alerta vermelho/verde de service incomodar por flapping, não silenciar o monitor primeiro. Investigar `journalctl -u <service>` e corrigir a causa do restart loop. Só ajustar debounce/threshold se o service estiver saudável e o alerta for realmente falso positivo.
