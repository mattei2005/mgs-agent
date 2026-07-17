# REPORT-INFRA — verificar entrega real antes de afirmar

## Contexto

Em 2026-07-02, agente legado corrigiu a pasta `CAR_BR_PT` no Google Drive e informou na thread que também havia enviado o `REPORT-INFRA` para `#alerts-infra`. Rodolfo não viu a mensagem e pediu verificação.

A auditoria do Zeus mostrou que o envio existia e retornou HTTP 204, mas o fluxo da agente legado ainda permitia afirmar “enviei” sem confirmar no Discord que a mensagem realmente apareceu no canal correto.

## Evidência confirmada

- Canal correto: `#alerts-infra` / `1498132022634483894`.
- Mensagem original encontrada via Discord API: `1522260849736286390`.
- Timestamp: `2026-07-02T15:21:08Z` / `11:21:08 EDT`.
- Autor: `Webhook - Alerts Infra Channel`.
- Conteúdo: `[REPORT-INFRA]` sobre correção `CAR_BR_PT`.
- Mentions presentes: Rodolfo (`344196393512075265`) e Zeus (`1496296175014252634`).

## Regra operacional

Quando um agente reporta infra fora da thread original, o sucesso só pode ser declarado após duas validações:

1. O helper de envio retorna sucesso real (`HTTP 204` ou status equivalente documentado).
2. A mensagem é localizada via Discord API no canal/thread esperado.

Não basta o script imprimir `sent=ok`; confirmar a presença no destino evita falsa confiança quando:

- o webhook aponta para outro canal;
- o envio saiu como embed vazio e passou despercebido;
- o canal correto foi confundido com outro canal de alertas;
- a mensagem truncou ou perdeu campos críticos.

## Helper preferencial

Use o helper canônico MGS quando disponível:

```bash
/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type skill \
  --path /path/to/artifact \
  --reason "motivo" \
  --evidence "commit/hash/output"
```

Evite usar helper nomeado por outro agente como padrão operacional (`ares-report-infra.sh`) quando existe helper genérico/canônico. Fallback textual é aceitável apenas quando o helper canônico não cobre o caso e a entrega for validada via API.

## Checklist antes de responder na thread original

- [ ] Canal alvo é `1498132022634483894` para `#alerts-infra`.
- [ ] Envio retornou `HTTP 204`/sucesso.
- [ ] Busca via Discord API encontrou a mensagem no canal/thread correto.
- [ ] Para report que requer processamento Zeus, ack canônico foi postado após inventário/audit: `✅ Registrado.` ou `✅ Registrado. Inventário atualizado (commit XXXX).`
- [ ] Só então dizer ao usuário que o `REPORT-INFRA` foi enviado.
