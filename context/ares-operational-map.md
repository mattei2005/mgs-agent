# Ares — Mapa Operacional HOT

> Status: proposta operacional v0.1  
> Dono executivo: Rodolfo Mattei  
> Agente: Ares  
> Função: reduzir `search_files` amplo e orientar a primeira fonte certa para Growth / Media Buying.

## 1. Regra de uso

Antes de buscar termos genéricos como `drive`, `campaign`, `meta`, `creative`, `CC_US_ES`, `UPLOAD`, `pixel`, `budget`, `roi`, `intraday`, `canva` ou nomes soltos de arquivos, Ares deve abrir este mapa e escolher a fonte específica.

Use `search_files` amplo apenas quando:

- o pedido trouxer termo novo que não esteja neste mapa;
- a fonte indicada não existir ou estiver incompleta;
- for auditoria de drift/inconsistência;
- Rodolfo pedir explicitamente para procurar em tudo.

## 2. Fontes principais do Ares

```text
Assunto                                Abrir primeiro
-------------------------------------- ------------------------------------------------------------
Arquitetura Growth/MGS OS              /root/mgs-agent/context/acquisition.md
Rotas e limites                         /root/mgs-agent/context/routes.md
Mapa de agentes                         /root/mgs-agent/context/agent-map.md
SOUL vivo do Ares                       /root/.hermes/profiles/ares/SOUL.md
SOUL versionado do Ares                 /root/mgs-agent/profiles/ares-soul.md
Skill umbrella aquisição                /root/mgs-agent/profiles/ares-skills/growth/paid-acquisition-operations/SKILL.md
Tráfego direto CBO/UTM/SB/SMS          /root/mgs-agent/profiles/ares-skills/growth/direct-traffic-cbo-operations/SKILL.md
Taxonomia criativos                     /root/mgs-agent/profiles/ares-skills/growth/creative-taxonomy-mgs/SKILL.md
Meta intraday                           /root/mgs-agent/profiles/ares-skills/growth/meta-ads-intraday-operations/SKILL.md
Meta guardrails                         /root/mgs-agent/profiles/ares-skills/growth/meta-ads-governance-guardrails/SKILL.md
Sanitizador metadata                    /root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
Wrapper sanitizador                     /root/mgs-agent/scripts/clean-creative-metadata.sh
Scripts Ares                            /root/mgs-agent/scripts/ares-*.py
Dados Ares                              /root/mgs-agent/data/ares/
Logs Ares                               /root/.hermes/profiles/ares/logs/
Audit MGS                               /root/mgs-agent/logs/events-audit.jsonl
```

## 3. Pergunta/pedido → fonte certa

```text
Pedido do usuário                                   Primeira fonte
-------------------------------------------------- ------------------------------------------------------------
"campanha" / "ads" / "growth"                    paid-acquisition-operations/SKILL.md
"Meta Ads" / "Facebook Ads"                       meta-ads-intraday-operations + guardrails
"corte intraday" / "reativar todas"               meta-ads-intraday-operations/SKILL.md
"budget" / "billing"                              SOUL + guardrails; exige confirmação/double-confirm quando crítico
"ROI" / "performance" / "CPS"                    dados/API real; não inventar sem fonte
"criativo para campanha"                           creative-taxonomy-mgs/SKILL.md + metadata sanitizer
"naming" / "taxonomia" / "P_ORIENT"               creative-taxonomy-mgs/SKILL.md
"Drive" / "UPLOAD_CANVAS"                         paid-acquisition-operations/SKILL.md seção Canva/Drive
"Canva"                                            paid-acquisition-operations/SKILL.md seção Canva
"limpar metadata"                                  docs/CREATIVE_METADATA_SANITIZER.md + clean-creative-metadata.sh
"handoff para Hera"                                routes.md + hera-operational-map.md
"Hera mandou criativo"                             creative-taxonomy-mgs/SKILL.md seção Entrada operacional via Hera
"ChatPion/quiz/SMS"                                routes.md; Ares não configura
"WordPress/site setup/pixel crítico"               routes.md; escalar Zeus/Rodolfo
"erro do Ares"                                     /root/.hermes/profiles/ares/logs/ + logs/ares-*.log
```

## 4. Meta Ads / intraday

Primeira fonte: `profiles/ares-skills/growth/meta-ads-intraday-operations/SKILL.md`.

```text
Estrutura local                         Pasta
--------------------------------------- ------------------------------------------------------------
Accounts/config por conta                /root/mgs-agent/data/ares/meta-ads/accounts/
Operações país+vertical                  /root/mgs-agent/data/ares/meta-ads/operations/
Rulesets R1-R5                           /root/mgs-agent/data/ares/meta-ads/rules/
Estado local/carência/exclusões           /root/mgs-agent/data/ares/meta-ads/state/
Cache                                    /root/mgs-agent/data/ares/meta-ads/cache/
Auditoria                                /root/mgs-agent/data/ares/meta-ads/audit/
Relatórios                               /root/mgs-agent/data/ares/meta-ads/reports/
Permissões/guardrails                    /root/mgs-agent/data/ares/meta-ads/permissions/
```

Scripts iniciais:

```text
/root/mgs-agent/scripts/ares-meta-common.py
/root/mgs-agent/scripts/ares-meta-auth-check.py
/root/mgs-agent/scripts/ares-meta-intraday-runner.py
```

Regras rápidas:

- leitura/dry-run antes de write;
- alteração de campanha precisa aprovação explícita;
- budget/billing é crítico e exige confirmação forte;
- não reportar sucesso sem GET/API real;
- não expor token Meta.

## 5. Criativos / Drive / Canva

Primeira fonte: `profiles/ares-skills/growth/creative-taxonomy-mgs/SKILL.md`.

```text
Item                                Regra
----------------------------------- ------------------------------------------------------------
Nome oficial                         {VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
VARIANT                              3 dígitos: 001-999
P_ORIENT                             somente PV, PH, NV, NH
Status                               não entra no nome; fica em pasta/inventário
Drive raiz                           MGS-CRIATIVOS
UPLOAD_CANVAS                        RAW/original; preservar salvo ordem explícita
Novos uploads via Hera               País + Vertical + Língua + anexo
Antes de campanha                    verificar/limpar metadata
```

Pipeline seguro para backlog/Drive:

```text
1. Inventário read-only fresco.
2. Validar IMG/VID pelo arquivo real.
3. Extrair dimensões/frame/timeline quando vídeo.
4. Classificar país/idioma/vertical/ângulo com evidência.
5. Gerar plano CSV/JSON com confidence/notes.
6. Mostrar plano para Rodolfo.
7. Só executar Drive write após aprovação explícita.
8. Preservar RAW e agir na cópia limpa quando aplicável.
```

## 6. Sanitização de metadata

Primeira fonte: `docs/CREATIVE_METADATA_SANITIZER.md`.

Comandos canônicos:

```text
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/asset
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/asset --agent ares
```

Ares não deve subir criativo bruto em campanha se o gate de metadata falhar ou estiver pendente.

## 7. Handoff Ares ↔ Hera

- Se Ares precisar resumir thread/config para Hera, enviar ao canal da Hera mencionando o bot Hera `1513006098133680290`.
- Se Hera enviar criativo novo válido, tratar como entrada operacional e seguir `creative-taxonomy-mgs`.
- Não mencionar Hera para status sem ação, agradecimento ou loop entre bots.

Formato mínimo para handoff Ares → Hera:

```text
[HANDOFF ARES → HERA]
Contexto da thread
Decisões feitas
Configurações/arquivos alterados
O que Hera precisa fazer
Bloqueios/riscos
```

## 8. Limites rápidos

```text
Ares pode                               Ares não pode por padrão
--------------------------------------  ---------------------------------------------------------
Analisar campanhas/performance           Configurar ChatPion/DigitalTrChat
Operar Meta/Google conforme aprovação     Configurar quiz/SMS/SMS Funnel
Preparar criativos para campanha          Ser dono de AdOps/Smart Bidding/ActiveView
Organizar taxonomia/Drive de campanha     Fazer setup WordPress/site/pixel crítico sem Rodolfo
Criar scripts/relatórios de growth        Expor credenciais/tokens
```

## 9. Validação antes de responder

- Métrica de campanha: citar fonte real/API/log/dado usado.
- Mudança Meta/Google: validar estado pós-ação com GET/API real.
- Drive write: validar item por ID/nome pós-ação, sem expor IDs sensíveis sem necessidade.
- Metadata: validar `verify clean=true`.
- Git/infra/script: reportar diff/status/log e `REPORT-INFRA` quando aplicável.
- Sem fonte real: declarar lacuna, não inventar performance.
