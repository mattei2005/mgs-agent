# HANDOFF — t_27706e88 — manutenção de coordenação Mavroa G006

## Resultado: HOLD seguro; implementação NÃO liberada

Este não é um recibo de conclusão técnica ou de campanha. O card de entrega existente **t_4ac36ea1** permanece dependente desta manutenção e é o único responsável pelas 28 cópias. Nenhuma campanha foi executada por esta etapa.

### Autoridade e lacuna exata

Foram lidos AGENT.md, permissions-matrix.md, routes.md, knowledge-governance.md e a referência obrigatória `campaign-runtime-recovery.md`. O pedido delimita diagnóstico, proteção e manutenção de coordenação, mas não contém decisão de Rodolfo aprovando uma nova semântica estrutural de retirada permanente de um writer histórico com QA material incompleto. A delegação Campaign Ops de Nicolas não inclui promoção de política/estrutura do runtime. Não foi identificada uma transição canônica existente que represente o takeover manual.

A decisão necessária é: **Rodolfo aprova acrescentar ao contrato central uma transição de encerramento exclusivamente de coordenação por takeover humano, distinta de COMPLETE/QA, para o request shein-1569456380065222707, integrando runner, Engine/activation, lease/readers, fila/worker/notifications e provas de mídia, sob recibo vinculado à mensagem humana e GET dos mesmos objetos?** A proposta não autoriza write Meta/Drive, mudança de campanha, reserva, revisão histórica, cron ou credencial. O nome/schema final do novo contrato precisa ser fechado na aprovação; nenhum rótulo foi instalado ou persistido como estado ativo.

Não basta um novo enum em queue.TERMINAL: o runner só reconhece dois terminais com summary e trata fase desconhecida como preparação; a ativação aceita retomar ACTIVATION_PENDING; AccountWriterLeaseStore.release grava COMPLETE. A capacidade ausente atravessa consumidores de produção e muda a regra de admissão do writer. Por isso não foi promovida unilateralmente a política ativa nem foi usada a liberação genérica da lease como atalho.

### Provas reais

- GET da mensagem 1569494300255985776 confirmou Nicolas `1055570806945620030`: “ativei as campanhas da conta uma a uma manualmente e aparentemente funcionaram / confere pra mim”. GET do novo pedido 1569495587005530205 confirmou as seis linhas, mesma origem; permissão live no pai 1548150155184701440 e thread 1558134703565967394 verificada.
- Readback Meta em 09/11/2026 18:42 EST: campanhas 102–110 e nove adsets ACTIVE; 16/18 ads ACTIVE. AD02 da 104 `120251118532380629` e da 108 `120251118590680629` PAUSED/WITH_ISSUES, código 2490468, sem motivo específico no feedback. Mesmos campaign/adset/ad/creative IDs da evidência anterior.
- Budgets preservados: 103=3500; demais oito=4375; total 38500 minor USD. Ativação é relato de Nicolas; autoria da alteração de budget continua não comprovada. Não há QA original integralmente concluído.
- Runner histórico permanece ACTIVATION_PENDING e lease bloqueante do request manual; state/checkpoint/manifests não foram editados.
- Job novo preservado sob `.dispatch.lock` e `.lock`, backup e CAS; apenas acrescentados maintenance_hold, dispatch_owner=foreground e delivery_owner=ares. Request, command, enqueued_at, attempts=0, status=WAITING, dependencies e notification=null preservados.
- `--inspect` real continua retornando **shein-1565261967260647536-c3** e **shein-1569456380065222707**. Não há prova de dependências vazias. A prova typed shein_source_media não pode ser promovida enquanto a lease manual continuar ativa; seu guard foi preservado, sem simular uma lease idle.
- Regressão instalada de source_media, decision_wait e request_queue: 87 testes únicos, 87 aprovados, zero falhas/erros/skips. É baseline, NÃO aceitação de uma transição ainda inexistente. Negativos existentes de mídia compartilhada/reserva/lease/locks e hold/foreground continuam verdes. Negativos do novo contrato e de aprovação faltante ainda são pendentes de implementação aprovada.
- Zero writes Meta/Drive, zero reserva/mídia nova, zero campanha executada, zero notificações de worker ou mensagens operacionais por esta manutenção. Nenhum código/config/serviço foi instalado, alterado ou reiniciado.

## Retomada após decisão estrutural

1. Validar por GET a decisão de Rodolfo e persistir escopo canônico; não interpretar novo pedido comercial como autorização estrutural.
2. Reconciliar o job049 e seu hold; preservar a proteção foreground. Coordenar writer único e verificar hashes/CAS de todos os consumidores antes da implementação. Não sobrepor mudanças de outro integrador.
3. Implementar/testar transição central sem terminal falso e sem modificar state/manifests históricos para fabricar QA. Recibo deve vincular request, conta, mensagens, IDs, estado vivo, deltas, relógio e hashes. Bloquear reexecução histórica em todos os entrypoints; não liberar nem transferir reservas por efeito da coordenação.
4. Exercitar negativos: aprovação ausente/errada, outro request/conta/autor, alterações de estado/IDs/selos, lease/writer concorrente, mídia compartilhada, reserva não terminal; testar reentrada/idempotência, falhas parciais, rollback e todos os consumidores. Backup/CAS/locks, hashes instalados, inventário e REPORT-INFRA com GET são obrigatórios.
5. Só depois da reconciliação canônica, executar `--inspect` com o input049 original; exigir dependências vazias e prova typed `shein_source_media` fresca (TTL 120s) demonstrando mídia disjunta e c3 histórico inerte/PAUSED. Não executar ou mudar o c3, estender review ou ignorar reserva.
6. Handoff de entrega exclusivamente ao card t_4ac36ea1. Este card de manutenção não executa campanha nem responde na thread operacional.

## Input imutável e comando condicional

Input exato:
`/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/049-request.json`

SHA256 do input: `cf30ab6521682266b2a00a2bdf3f89ee0ad43e19acdf6cd343d4908dbc6e7d85`.

**NÃO executar agora** (dependências presentes). Após todos os critérios técnicos acima e autorização live revalidada, o dono da entrega usa:

```text
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/049-request.json
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --take-foreground /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/049-request.json
```

O takeover canônico precisa remover o hold somente após deps vazias, com dispatch_owner foreground e sem avisos individuais. A entrega revalida os seis inputs originais/relógio/horário e executa o runner central no seu próprio card. As 28 cópias ainda não foram criadas. Nenhum relatório de manutenção deve ser postado na thread operacional e nenhum final de campanha deve ser publicado por esta etapa.
