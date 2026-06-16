# OpenzedFinanzas-CC-ES — piloto Meta Ads Messenger

Resumo operacional do primeiro piloto Ares para gestão de tráfego Meta Ads focado em Messenger/chatbot.

## Decisões do piloto

```text
Campo                         | Decisão
------------------------------|------------------------------------------------------------
Operação                      | OpenzedFinanzas-CC-ES
Conta piloto                  | 1356770869843984
Conta Meta lida               | OpenzedFinanzas-ES-CC-ES-03
Business                      | Mattei Services Inc
Canal                         | Messenger
Nível de ação                 | Campaign somente
Cortes intraday               | A cada 30 minutos
Reativar-todas                | 00:30 no timezone da conta Meta
Timezone detectado            | Europe/Madrid
Moeda detectada               | USD
Budget referência usuário     | R$1.500/dia, não é kill switch
Log intraday                  | Só quando houver ação/erro
Permissão piloto              | Só Rodolfo autoriza alterações
Token                         | 1Password item `Token Meta API`, campo `credential`, nunca expor valor
```

## Estrutura criada

```text
/root/mgs-agent/data/ares/meta-ads/accounts/1356770869843984.json
/root/mgs-agent/data/ares/meta-ads/operations/OpenzedFinanzas-CC-ES.json
/root/mgs-agent/data/ares/meta-ads/rules/openzedfinanzas_cc_es_intraday_v1.json
/root/mgs-agent/data/ares/meta-ads/permissions/pilot-permissions.json
/root/mgs-agent/data/ares/meta-ads/state/reactivate-exclusions.json
/root/mgs-agent/data/ares/meta-ads/state/campaign-test-grace.json
/root/mgs-agent/data/ares/meta-ads/cache/campaigns-1356770869843984-latest.json
/root/mgs-agent/data/ares/meta-ads/audit/auth-check-1356770869843984.json
```

Scripts:

```text
/root/mgs-agent/scripts/ares-meta-common.py
/root/mgs-agent/scripts/ares-meta-auth-check.py
/root/mgs-agent/scripts/ares-meta-fetch-campaigns.py
/root/mgs-agent/scripts/ares-meta-intraday-runner.py
```

## Validações feitas

```text
Check                         | Resultado
------------------------------|------------------------------------------------------------
1Password item                | Encontrado
Token exposto no chat         | Não
Meta account GET              | HTTP 200
Campaigns GET                 | HTTP 200
Campanhas retornadas          | 15
Ativas                        | 5
Pausadas                      | 10
TEST no nome                  | 0 no primeiro snapshot
```

## Lições reutilizáveis

1. Service Account do 1Password precisa de `--vault` explícito em `op item get`; use `OP_DEFAULT_VAULT` ou fallback `MGS Conteúdo`.
2. Ao reportar token, mostrar somente item/campo/len/status; nunca o valor.
3. Meta `currency` e timezone devem vir da conta, não do VPS nem da suposição do usuário.
4. Se o usuário definir teto em moeda diferente da conta, registrar como referência até confirmar regra de conversão.
5. Intraday determinístico deve ficar separado do gestor inteligente diário; a camada inteligente futura pode considerar ROI drip/ROI geral via Lovable, mas não deve bloquear a primeira etapa de leitura/dry-run.
6. Criar R1-R5 como slots desabilitados `pending_definition`, não inventar condições de corte.
