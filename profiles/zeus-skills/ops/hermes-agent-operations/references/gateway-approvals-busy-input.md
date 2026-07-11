# Gateway Approvals and Busy Input

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 5. Gateway approvals / execução sem prompts para agentes confiáveis

Use quando Rodolfo pedir para um agente MGS confiável parar de pedir `Command Approval Required`, `Allow Once`, `Allow Session` ou `Always Allow` para operações técnicas que já fazem parte do escopo do agente — exemplo: Hera rodando `execute_code`/terminal para processar Drive/criativos quando Kelly/Rodolfo já pediu a ação.

Regra operacional MGS: se Rodolfo disser “se pediu é pra fazer”, “não quero esse tipo de notificação”, “dá autorização total” ou equivalente para um agente confiável, a correção é no profile do agente, não em cada thread expirada.

Fluxo seguro:

1. Confirmar que o pedido é sobre o **gate técnico de execução Hermes** (`tools/approval.py`) e não sobre liberar novos usuários externos.
2. Fazer backup pequeno do config vivo do agente antes da mudança.
3. Setar no profile afetado:

```bash
hermes -p <agent> config set approvals.mode off
```

4. Preferir gravar explicitamente como string YAML para evitar ambiguidade visual:

```yaml
approvals:
  mode: 'off'
```

5. Atualizar também o mirror versionado em `/root/mgs-agent/profiles/<agent>-config.yaml` quando existir, para não haver drift entre runtime e Git.
6. Validar carregando YAML dos dois arquivos e confirmando `approvals.mode == 'off'`.
7. Registrar em `/root/mgs-agent/logs/events-audit.jsonl` com requester, agente, paths e razão.
8. Reportar curto: “sem restart necessário” quando aplicável. `tools/approval.py` lê o config no momento do check; não precisa reiniciar gateway só para essa chave.

Pitfalls:

- O prompt expirado atual não é reaproveitado; o agente precisa tentar de novo. A próxima tentativa deve passar direto.
- `approvals.mode: off` desliga prompts de comandos/`execute_code` para aquele profile. Isso **não** libera usuários novos, não altera `DISCORD_ALLOWED_USERS` e não bypassa a autorização de canal/whitelist.
- Não confundir com `approvals.cron_mode`; cron continua separado e deve permanecer `deny` salvo pedido explícito.
- Não usar `/yolo` como solução permanente para agente MGS; `/yolo` é sessão/processo. Config de profile é a correção durável.

## 5.1 Mensagens enviadas enquanto o agente está ocupado

Use quando o usuário disser que uma segunda mensagem enviada durante “digitando” só é processada depois da primeira resposta, ou quando quiser consolidar complementos no turno em andamento.

Playbook detalhado de diagnóstico, rollout multiagente, restart e smoke funcional: `references/hermes-busy-input-steering-mgs.md`. A referência também mapeia o fluxo Discord end-to-end (`Attachment` → cache → `MessageEvent` → busy handler → `AIAgent.steer`), o gap de mídia quando só `event.text` é steered, o contrato de payload com paths agent-visible, nuances VOICE vs AUDIO/STT, role alternation, dedup/replay e a matriz de testes multimodais.

Diagnóstico obrigatório no estado vivo:

1. Ler `display.busy_input_mode` no `config.yaml` do profile.
2. Confirmar o valor resolvido com o Python do venv Hermes chamando `GatewayRunner._load_busy_input_mode()` e `_load_busy_text_mode()`.
3. Não chamar mid-turn steering de “ativo” apenas porque o código `/steer` existe.

Semântica:

- `queue`: preserva a execução atual e processa a nova mensagem no turno seguinte; corresponde ao sintoma “espera terminar e depois responde”.
- `interrupt`: interrompe/redireciona a execução atual; não garante uma resposta consolidada.
- `steer`: injeta o payload do usuário na execução em andamento no próximo ponto seguro, permitindo ajustar o trabalho e consolidar a resposta final.

**Regra MGS obrigatória definida por Rodolfo:** o comportamento mid-turn deve funcionar para qualquer mensagem enviada enquanto o agente está ocupado: texto, imagem, imagem com texto, áudio, áudio com texto e demais anexos. Mídia não pode cair silenciosamente para `queue` só porque o `AIAgent.steer()` aceita texto; o gateway deve converter o evento já normalizado (caption/transcrição + marcadores e caminhos locais dos anexos) em um payload de steer confiável, sem duplicar a mensagem no próximo turno. Se o Hermes stock não suporta uma modalidade, tratar como gap de runtime a corrigir e testar, não como limitação aceitável do produto MGS.

**Correção de comunicação/diagnóstico:** se o usuário mostrar `Queued for the next turn` em uma mensagem com imagem/áudio, não defender a configuração dizendo apenas “o `steer` funciona para texto” ou “não foi falha da configuração”. Isso pode explicar a causa técnica, mas continua sendo falha do requisito MGS universal. Separar sempre três camadas: (1) config resolvida em `steer`; (2) runtime capaz de serializar aquela modalidade; (3) smoke funcional comprovando incorporação sem replay. Só a terceira permite dizer que o comportamento pedido funciona.

Para o comportamento “mandei um complemento enquanto estava digitando; incorpore e responda uma vez”, o modo correto continua sendo:

```yaml
display:
  busy_input_mode: steer
```

### Pitfall: sessão ocupada antes do `AIAgent` existir

Ver `Queued for the next turn` não prova que o profile voltou para `queue`. Compare sempre config vivo, valor resolvido e estado de `_running_agents[session_key]`. O gateway pode já mostrar “digitando” enquanto a sessão ainda contém `_AGENT_PENDING_SENTINEL`.

No runtime MGS corrigido, follow-up recebido nessa janela deve:

1. reservar uma sequência FIFO **antes** de STT/enrichment assíncrono;
2. incrementar uma contagem de preprocessamentos em voo e preservar o `MessageEvent` completo;
3. bloquear a promoção do sentinel apenas na worker thread — nunca no event loop — até todas as reservas terminarem;
4. drenar o buffer em ordem de chegada e promover o agente de forma atômica sob a mesma `Condition`/lock;
5. aplicar `_merge_startup_steer_into_message` antes da primeira chamada ao modelo e alinhar qualquer `persist_user_message` override com a mensagem realmente mesclada;
6. reler geração e identidade do agente depois de qualquer `await`; payload atrasado nunca pode ser enviado a agente encerrado ou substituído;
7. limpar buffer, sequence, inflight e janela aberta em stop, erro e finalização, acordando waiters;
8. produzir ack de `Steered`, nunca `Queued`, quando a reserva foi aceita.

Guard obrigatório após updates: confirmar `_reserve_startup_steer`, `_complete_startup_steer`, `_promote_agent_and_consume_startup_steers`, `_try_busy_steer_event`, `_merge_startup_steer_into_message`, `test_startup_barrier_waits_and_preserves_arrival_order` e `test_async_prepare_does_not_steer_into_replaced_agent`. Para reproduções reais, usar o Discord como fonte direta e comparar os timestamps do pedido inicial e do complemento; sessão Hermes é contexto secundário.

### Pitfall: editar depois de validar/agendar restart

Nunca agendar restart enquanto revisão independente ainda estiver pendente. Depois de preparar ou agendar o finalizer, runtime e configs-alvo ficam congelados. Se surgir achado tardio: cancelar/pausar a execução destacada, corrigir, rodar novamente lint/compilação/testes/guard, gerar novo snapshot e só então agendar outro finalizer.

`py_compile` não detecta chamada a método de instância inexistente. O preflight de restart precisa comparar helpers críticos chamados versus definidos. O finalizer seguro também deve registrar SHA-256 dos targets validados e abortar antes de reiniciar qualquer gateway se houver drift, falha de compilação ou helper startup sem definição.

Mudança de `config.yaml` ou runtime é infra: só aplicar quando solicitada, validar valor resolvido, patch canônico, testes e restart seguro. Não prometer consolidação quando a mensagem chega depois do final; enquanto o turno ainda estiver ativo, todas as modalidades devem entrar no mesmo turno.
