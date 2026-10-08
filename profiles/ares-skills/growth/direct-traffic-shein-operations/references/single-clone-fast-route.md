# SHEIN — rota curta de duplicação individual

## Escopo instalado

Use `scripts/ares-shein-campaigns.py single-clone` para **uma duplicação igual, PAUSED, solicitada por Rodolfo**, na conta exata `Yolokfx-US-SHEIN-EN-01-G002` / `7840111366055613`. O adapter é `ares_campaign_v3.shein_single_clone`; todo write continua exclusivamente em `CampaignEngine v3`. Não ampliar para ACTIVE, outro gestor, outra conta, novos assets ou outros modos por inferência.

O rollout preserva o runner G005 de três modos. Não usar `prepare-live/materialize` G005 para este pedido, não remontar o manifest em Python ad hoc e não editar scripts dentro de uma transação de campanha.

## Consulta de contas dos seis gestores

Fonte canônica: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json`. Contém somente contas com SHEIN no nome, IDs Meta, suffix G001–G006, vínculo ao gestor/canal, moeda, timezone e snapshot API. Consulta rápida, sem abrir BM de novo:

```text
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py account-lookup \
  --account Yolokfx-US-SHEIN-EN-01-G002 --manager-code G002
```

Nos canais de gestor, passar também `--channel-id` do canal pai canônico. Resolver somente nome completo ou ID exato; alias parcial, duplicado ou gestor/canal divergente falha fechado. Rodolfo pode consultar a operação global. Cadastro de lookup não concede permissão, não onboarda automaticamente outras contas e não transforma `engine_registered` do snapshot em autorização atual. O runner relê o config e a conta viva.

## Pedido natural → uma chamada

Materializar somente o JSON de intenção, sem perguntas sobre IDs técnicos. Campos:

```json
{
  "request_id": "shein-g002-MESSAGE_ID-pureclone",
  "account": "Yolokfx-US-SHEIN-EN-01-G002",
  "source_number": 110,
  "budget_usd": "30",
  "start_time": "2026-10-08T00:00:00-04:00",
  "status": "PAUSED",
  "authorized_by": "344196393512075265",
  "source_thread_id": "1557274000680288307"
}
```

Os valores acima são exemplo de shape, não um pedido futuro nem defaults de data/budget/fonte. Usar request ID novo derivado da mensagem real quando disponível. Se o gateway entregar `source_message_id`, incluí-lo exatamente como string no JSON: o runner extrai o timestamp do snowflake e mede **criação da mensagem → readback**, incluindo preparação do agente. Não usar ID da thread/canal como message ID e não inventar timestamp. Se houver timestamp real de recebimento, `request_received_at` ISO aware tem prioridade e a medição é identificada como gateway receipt. Sem ambos, reportar somente duração do runner, nunca E2E completo.

```text
# Análise live sem criação (para calibração fora da transação)
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py single-clone \
  --input <request.json> --dry-run

# Pedido humano já autorizado: preflight → selo/plan → Engine → readback
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py single-clone \
  --input <request.json> --confirm-execute
```

Não fazer um dry-run separado antes de toda execução normal: a mesma chamada já realiza validação e plan offline antes do primeiro write, além de repetir a conciliação da numeração imediatamente antes do Engine. Sem `--confirm-execute`, o comando é read-only. `--dry-run` e confirmação juntos são rejeitados.

## Guards e recovery

- Lookup local exato; domínio autorizado; Rodolfo no registry; conta ativa USD/ET/ADVERTISE; identidade corporativa; evento Add to Wishlist e CBO; Page ADVERTISE e pixel associado.
- Uma campanha e um adset fonte, 1–5 ads únicos; tracking específico `b01fb01cNNN` / `g002-s`; URL original específica da conta e source post verificados. Nome novo preserva produto/qualificadores, data local do início e `COPY Cfonte`; numeração usa máximo live +1.
- Somente `pure_clone` e rota `existing_post_two_phase`, sem `adset_updates` ou mídia nova. Não fazer tentativas de reescrever flags que a Meta já normalizou. Diferença opcional age/gender é ressalva explícita, nunca alegação de cópia 100% idêntica; outros drifts falham fechado.
- Token corporativo cache-first; Page token uma vez por Page, apenas em memória; posts únicos em batch; `shares` ausente é desconhecido.
- Account lock do adapter mais guards do Engine; state selado persistido antes do execute. Mesmos parâmetros/request retomam o mesmo manifest. Request ID com parâmetros diferentes é rejeitado. IDs do Engine persistidos; pós-processamento falho retoma somente leitura, sem recriar campanha.
- State: `data/ares/meta-ads/state/shein-campaigns/single-clone/<request_id>/state.json`. Audit final: `data/ares/meta-ads/audit/shein/campaigns/single-clone/<request_id>-final.json`. Em quota/recovery, retomar o mesmo comando com o input original; não dormir em foreground, não trocar request e não repetir POST manual. O core permanece dono da recuperação de layers.
- Resumo traz ID, status, source lineage, budget/schedule, ads/posts/UTM, warnings, budget ativo/delta, timers de preparação/Engine/pós/total e contadores separados HTTP-read versus GETs lógicos. Não narrar preparação na conversa; entregar fechamento curto.

## Verificação fora da transação

```text
python3 -m unittest discover -s /root/mgs-agent/tests -p test_shein_single_clone_route.py -v
python3 -m unittest discover -s /root/mgs-agent/tests -p test_ares_shein_campaigns_v3.py -v
```

Novo pedido real continua obrigatório para medir ganho E2E de criação. Dry-run rápido e testes fake não são criação nem canário autorizado. Fonte oficial do timestamp snowflake: https://docs.discord.com/developers/reference.
