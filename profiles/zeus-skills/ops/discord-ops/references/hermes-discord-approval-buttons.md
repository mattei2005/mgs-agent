# Hermes Discord Approval Buttons — diagnóstico e mitigação

Use quando o usuário relatar prompts frequentes de aprovação no Discord ou erro visual `This interaction failed` ao clicar em `Allow Once / Allow Session / Always Allow / Deny`.

## Sintomas

```text
Sintoma                         | Causa provável
--------------------------------|------------------------------------------------------------
Prompts de approval demais       | approvals.mode=manual + Tirith/dangerous scanner gerando falsos positivos.
This interaction failed          | Discord não recebeu ACK do componente em ~3s.
Botão parece falhar, mas log resolve | Handler resolveu fila tarde demais ou editou mensagem antes de defer.
Raw IP marcado MEDIUM            | Tirith alerta URL/IP direto; comum em infra RunCloud sem DNS interno.
```

## Diagnóstico mínimo

```bash
# Logs recentes do profile afetado
PROFILE=zeus
tail -120 /root/.hermes/profiles/$PROFILE/logs/errors.log

grep -Ei 'approval|interaction|component|button|allow once|allow session|deny|failed|timeout|expired|security scan' \
  /root/.hermes/profiles/$PROFILE/logs/agent.log | tail -120

# Config atual de approvals
sed -n '/^approvals:/,/^[^ ]/p' /root/.hermes/profiles/$PROFILE/config.yaml

# Runtime Hermes onde fica o handler Discord
python3 -m py_compile /root/.hermes/hermes-agent/gateway/platforms/discord.py
```

Mascarar tokens/senhas antes de colar output no chat.

## Fix validado: ACK imediato no botão Discord

Em `gateway/platforms/discord.py`, na classe `ExecApprovalView`, o método `_resolve()` deve reconhecer a interação antes de fazer trabalho que possa demorar:

```python
try:
    await interaction.response.defer(ephemeral=True)
except Exception:
    logger.debug("Discord approval defer failed", exc_info=True)

# depois: resolve_gateway_approval(...), ajusta embed, desabilita botões
try:
    await interaction.message.edit(embed=embed, view=self)
except Exception:
    logger.debug("Discord approval message edit failed", exc_info=True)
```

Ponto importante: não usar `interaction.response.edit_message(...)` depois de `defer()`; editar via `interaction.message.edit(...)`.

## Mitigação de ruído: smart approvals

Para perfis operacionais MGS onde Rodolfo está conduzindo manutenção ativa, usar:

```yaml
approvals:
  mode: smart
  timeout: 60
  gateway_timeout: 900
  cron_mode: deny
```

Racional:
- `smart` tenta auto-aprovar falsos positivos claros antes de abrir botão.
- `gateway_timeout: 900` evita timeout durante decisões humanas em tarefas longas.
- Hardline blocks continuam ativos em `tools/approval.py` e não devem ser bypassados.

Não usar `approvals.mode: off` sem autorização explícita do Rodolfo.

## Validação e rollout

1. `python3 -m py_compile gateway/platforms/discord.py` no venv/runtime Hermes.
2. Validar YAML do profile.
3. Restart controlado do gateway afetado (`zeus-gateway.service` ou `atena-gateway.service`).
   - Em conversa via o próprio gateway afetado, não faça restart foreground esperando resposta longa: o turno pode ser interrompido quando o serviço cair.
   - Preferir disparar restart em background/one-shot, avisar que a validação vem no próximo turno, e depois confirmar com `systemctl is-active`, `ActiveEnterTimestamp` e `journalctl --since`.
   - Se o process tracker do Hermes perder o `session_id` após restart, não tratar como falha do restart; validar pelo systemd/logs.
4. Teste real: disparar um comando approvable de baixo risco e clicar `Allow Once`.
5. Confirmar no log:

```text
Discord button resolved N approval(s) for session ...
```

6. Confirmar que a mensagem do botão foi editada/desabilitada sem `This interaction failed`.

## Pitfalls

- `This interaction failed` é erro do Discord client por falta de ACK rápido; não significa necessariamente que a fila Hermes não resolveu.
- Se o patch foi aplicado no arquivo runtime mas o service não reiniciou, a mitigação ainda não está ativa.
- Tirith `URL uses raw IP address` pode ser aceitável em infra interna MGS, mas ainda deve passar por smart/manual approval quando o contexto for ambíguo.
- Não transformar esse caso em allowlist ampla para qualquer raw IP; preferir smart approval e refatorar scripts para nomes/known_hosts quando fizer sentido.
