### Formato REPORT-INFRA (Atena/Ares/Hera → Zeus)

Ao processar `[REPORT-INFRA]`, seguir o playbook operacional em `references/report-infra-processing-playbook.md`: validar artefatos/hashes/crons, atualizar `infra-inventory.json` quando aplicável, registrar audit log, commitar só arquivos relevantes e responder apenas com o ACK canônico curto.

**Regra de roteamento para Zeus em tarefa interativa:** não despejar o bloco `[REPORT-INFRA]` na thread onde Rodolfo pediu a execução. Essa thread deve receber só conclusão/detalhes úteis. O report formal deve ser enviado ao canal correto de infra (`#alerts-infra` / webhook correspondente, com mention quando for thread nova). Se o report precisar existir como evidência, poste lá primeiro e depois responda na thread original com resumo limpo. Se a sessão atual não tiver rota/API para postar no canal certo, registre audit/inventário e não simule o report dentro da thread. Referência: `references/report-infra-thread-destination-pitfall-2026-07-01.md`.

**Verificação de entrega obrigatória:** antes de dizer na thread original que um `REPORT-INFRA` foi enviado, validar duas coisas: (1) helper/webhook retornou sucesso real (`HTTP 204` ou equivalente); (2) Discord API mostra a mensagem no destino esperado (`#alerts-infra` / `1498132022634483894`, ou thread específica quando aplicável). Isso evita falso positivo quando o webhook aponta para outro canal, mensagem sai como embed vazio, ou o agente confunde canais de alerta. Detalhe: `references/report-infra-delivery-verification-2026-07-02.md`.

**Layout obrigatório novo:** REPORT-INFRA enviado por Zeus deve usar embed Discord, não bloco de texto cru. Use o helper canônico:

```bash
/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type script/data \
  --path '/root/mgs-agent/scripts/foo.sh; /root/mgs-agent/data/infra-inventory.json' \
  --reason 'motivo operacional curto' \
  --evidence 'bash -n OK; dry-run OK; HTTP 204'
```

O helper mantém `content` vazio por padrão: sem mention do Zeus, do Rodolfo ou de qualquer pessoa. Ação/Tipo/Path/Motivo/Evidência ficam em fields de embed. Em `#alerts-infra`, REPORT-INFRA/alerta operacional normal é silencioso e não abre thread. Só usar mention em alerta crítico real com push explicitamente necessário. Não voltar para `[REPORT-INFRA] ...` em texto corrido salvo emergência/manual fallback.

Detalhe/pitfall validado: `references/report-infra-embed-no-mention-no-thread-2026-07-02.md`.

Formato legado ainda aceito para reports vindos de outros agentes, mas deve ser migrado quando tocarmos os scripts/procedimentos deles:
```text
[REPORT-INFRA] <@1496296175014252634> <@344196393512075265>
Ação: criada/modificada/removida
Tipo: cron / skill / script / config / data
Path: caminho exato
Motivo: contexto
Evidência: hash de commit ou output de comando
```

