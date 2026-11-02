# Handoff técnico — t_0c21790b → t_a4927be0

## Resultado e limites

Manutenção concluída, não entrega de campanhas. Nenhum execute de campanha, write Meta/Drive, upload ou reserva de inventário neste card. Nenhuma mensagem de manutenção na origem operacional. Fontes reais 011,010,012,009,008 lidas na conta exata 937846586033361: duas mídias IMG por fonte, dez linhagens de inventário, sem identidade compartilhada com o histórico 006/007. A equivalência de source_ad_id estrutural entre templates NÃO foi confundida com equivalência de mídia.

Os cinco jobs foram preservados sob dispatch/job locks e maintenance_hold antes de alterar código. Após provas reais e testes, takeover pelo CLI canônico dos mesmos inputs: todos FOREGROUND_OWNED, dispatch_owner=foreground, dependencies=[], attempts=0, notification=null, sem hold remanescente. O worker não executa nem envia conclusões individuais de jobs foreground. Serviço existente recarregado somente com todos os jobs inertes e dispatch locks adquiridos; ativo/heartbeat fresco. Zero restart de gateway.

Histórico shein-1565261967260647536-c3: decisão material UNANSWERED; campanhas 120250921178510629 (006) e 120250921178500629 (007), seus conjuntos e seis anúncios continuam PAUSED por GET fresco. IDs/mídias primárias conferidos com checkpoint; state, checkpoint e registro de decisão não mudaram. Não ativar/resolver/cancelar esse histórico como efeito do novo lote.

## Inputs imutáveis — ordem obrigatória

Raiz absoluta: /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331/

- c011.json — SHA256 0338042f8f87a15e6c544941985c051a5847835a7b99741dd2875c155fe22d02; fonte 120250944872210629.
- c010.json — SHA256 b82a8c5ed31ae5938f3cba64f07699c1ee721d30da14238158f1c7dd9e0f97ae; fonte 120250944872190629.
- c012.json — SHA256 c3ac246682285531627cc846feb2f21705c891e65fe4d902cc2a10d168f6365f; fonte 120250944885400629.
- c009.json — SHA256 de91965e809698b2225733b1573fb1d9f1aa99dc04a801c123bc635a0c96e905; fonte 120250943717660629.
- c008.json — SHA256 0a90440a625ed377f41d2a9bb160b2dfda267614796a13b862c9444c4d15c2bb; fonte 120250943717650629.

Cada input mantém quantity=5, budget_usd="45", início literal 2026-11-03T00:12:00-05:00, requester1055570806945620030, mensagem1566932068317921331, pai1548150155184701440 e thread1558134703565967394. O agregador aggregate-progress.json não foi alterado pela manutenção. Nenhum manifest foi editado. O preflight antigo 016 NÃO reserva numeração e não deve ser reutilizado sem nova leitura.

## Comandos centrais — SOMENTE no card de entrega

Executar em /root/mgs-agent, profile ares. Verificar a preservação dos hashes e a ausência de outro executor primeiro.

```bash
python3 /root/mgs-agent/scripts/mgs-ares-asset-scope.py check-account 937846586033361 --json
python3 /root/mgs-agent/scripts/mgs-domain-scope.py check --agent ares mavroa.com
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331/c011.json
```

Repetir inspect para c010,c012,c009,c008. O resolver obtém prova nova, não confia no JSON auditado como cache. Se dependência reaparecer, diagnosticar a causa atual; nunca remover manualmente. Os cinco já estão foreground-owned: não recriar jobs. Se for indispensável renovar explicitamente a posse após readback, o comando idempotente de handoff (zero campanha) é:

```bash
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --take-foreground /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331/c011.json
```

Para CADA input na ordem, imediatamente antes de sua execução e só após concluir a linha anterior:

```bash
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331/c011.json --dry-run
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331/c011.json --confirm-execute
```

Substituir somente o filename da linha atual; nunca regenerar request, manifest, SLA ou request IDs. Não usar laço cego de execute. Em efeitos parciais/quota, reconciliar IDs existentes e retomar exclusivamente o mesmo input pelo runner, sem repetir camada já criada. O guard preserva lease do MESMO request resumível com comparação integral ao input/defaults canônicos; budget/canal/conta divergentes continuam bloqueados.

## Aceitação operacional ainda pendente

O card t_a4927be0 é o único dono da entrega. Exigir 25 campaign IDs únicos reais, QA semântico e renderizado integral por ad/creative ID, pós-processamento, tracking/nomes/horário/lance/budget corretos, readback ACTIVE de campanhas/conjuntos/anúncios e GET da conclusão única na thread original. Atualizar aggregate-progress.json a cada linha. A manutenção e FOREGROUND_OWNED não comprovam criação ou ativação. Não escrever sobre testes/paths/fila na thread.

## Provas absolutas

- Backup/inventário anterior: /root/mgs-agent/work/t_0c21790b/before/ e before-inventory.json.
- Código instalado + SHA256: /root/mgs-agent/work/t_0c21790b/installed-digests.json.
- READ_ONLY real: /root/mgs-agent/work/t_0c21790b/real-readonly-validation.json — cinco inputs, 45 GETs lógicos/20 chamadas HTTP read-only, zero provider writes.
- Preservação/readback dos jobs: /root/mgs-agent/work/t_0c21790b/preservation-readback.json.
- Takeover CLI: /root/mgs-agent/work/t_0c21790b/foreground-takeover.json.
- Regressões: /root/mgs-agent/work/t_0c21790b/regression.xml e full-regression.log — 544 casos únicos, 492 subtestes, 44 arquivos; zero falha/erro. Primeira tentativa do runtime isolado faltava websockets; repetido com dependências completas, sem mudar runtime produtivo.
- REPORT-INFRA com GET real: /root/mgs-agent/work/t_0c21790b/report-infra-readback.json — mensagem1566936782417961032, canal1498132022634483894, content vazio, um embed, sem mentions/thread.
- Skill canônica atualizada: /root/.hermes/profiles/ares/skills/growth/direct-traffic-shein-operations/references/campaign-runtime-recovery.md, seção Pure clone sem asset_refs. Registro ares-shein-pure-clone-queue-media validado por mgs-knowledge-control.py.

Código novo shein_source_media.py é scheduling READ_ONLY, não mídia nova. Mantém fail-closed para source ambíguo, fonte/mídia/lineage ausente, thumbnail sem mídia primária, paginação incompleta, partição errada, recibo stale, inventário/state/checkpoint/registro alterado, histórico ativo ou mídia alterada, reserva ativa, lease/writer concorrente e mídia compartilhada. Recibos não autorizam writes e não transferem reservas.

Rollback: manter posse foreground e reconciliar qualquer efeito do card de entrega antes de restaurar código do backup. Nunca restaurar jobs antigos, limpar reservas, falsificar conclusão histórica ou modificar manifests para contornar guards.
