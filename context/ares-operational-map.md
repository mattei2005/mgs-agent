# Ares — Mapa Operacional HOT

> Status: proposta operacional v0.2
> Dono executivo: Rodolfo Mattei
> Agente: Ares
> Área: Creative Operations + Growth / Media Buying
> Atualização: capacidades da Hera consolidadas em 2026-07-12.

## 1. Regra de uso

Antes de busca ampla por `drive`, `creative`, `reference`, `video`, `meta`, `campaign`, `UPLOAD`, `budget`, `roi`, `canva` ou nomes soltos, abrir este mapa e escolher a fonte específica.

Busca ampla só quando a fonte indicada não existir, o termo for novo, houver auditoria de drift ou Rodolfo pedir para procurar em tudo.

## 2. Fontes principais

```text
Assunto                                Abrir primeiro
-------------------------------------- ------------------------------------------------------------
Identidade, autoridade e invariantes    /root/.hermes/profiles/ares/SOUL.md
Rotas e limites                         /root/mgs-agent/context/routes.md
Permissões reais                        /root/mgs-agent/data/authorized-users.json
Matriz conceitual                       /root/mgs-agent/context/permissions-matrix.md
Creative Ops                            creative-operations-mgs/SKILL.md
Taxonomia/linhagem/reserva              creative-taxonomy-mgs/SKILL.md
Meta/Facebook Ad Library                meta-library-reference-intake/SKILL.md
Aquisição geral                         paid-acquisition-operations/SKILL.md
Meta intraday                           meta-ads-intraday-operations/SKILL.md
Meta guardrails                         meta-ads-governance-guardrails/SKILL.md
Tráfego direto CBO/UTM                  direct-traffic-cbo-operations/SKILL.md
Sanitizador metadata                    /root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
Dados criativos                         /root/mgs-agent/data/ares/creative-ops/
Inventário unificado                    /root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl
Dados Meta Ads                          /root/mgs-agent/data/ares/meta-ads/
Scripts Ares                            /root/mgs-agent/scripts/ares-*
Logs Ares                               /root/.hermes/profiles/ares/logs/
Audit MGS                               /root/mgs-agent/logs/events-audit.jsonl
```

## 3. Pedido → primeira rota

```text
Pedido                                           Primeira fonte
------------------------------------------------ ------------------------------------------------------------
"faz um criativo/brief/copy"                    creative-operations-mgs route-pack-01
"trata/move UPLOAD MANUAL"                      creative-operations-mgs route-pack-02
"imagem estática/naming/provider"               creative-operations-mgs route-pack-04
"vídeo/variação/referência/GPT/Grok"            creative-operations-mgs route-pack-05
"Meta Ad Library"                               meta-library-reference-intake
"inventário/reserva/ares_eligible"              creative-taxonomy-mgs route-pack-02
"esse criativo já foi usado?"                   creative-operations-mgs route-pack-06 + Meta real
"campanha/ads/growth"                           paid-acquisition-operations
"Meta/Facebook Ads"                             meta-ads-intraday-operations + guardrails
"tráfego direto/CBO"                            direct-traffic-cbo-operations
"budget/billing"                                SOUL + guardrails + autoridade vigente
"ROI/performance"                               API/dados reais; período/moeda/fonte
"ChatPion/quiz/SMS"                             routes.md; Ares não configura
"WordPress/pixel crítico"                       routes.md; escalar Zeus/Rodolfo
"erro do Ares"                                  logs Ares + journal filtrado se infra
```

## 4. Ciclo único do criativo

```text
pedido/upload
→ criação/importação
→ referência/provider gate
→ classificação técnica/visual
→ sanitização
→ naming
→ Drive + readback
→ inventário e linhagem
→ reserva/elegibilidade
→ conciliação Meta × Drive
→ seleção/campanha
→ performance/ROI
→ novas variações
```

Não existe handoff Hera → Ares. Creative Ops e Campaign Ops compartilham o mesmo estado.

## 5. Intake e Drive

Raiz operacional atual validada:

```text
MGS-AGENTS/CRIATIVOS/
├── UPLOAD MANUAL
└── <OPERAÇÃO>/
    ├── IMG/{01_READY,02_TESTING,03_TESTED,04_WINNERS,05_REJECTED,99_LEGACY}
    └── VID/{01_READY,02_TESTING,03_TESTED,04_WINNERS,05_REJECTED,99_LEGACY}
```

Regras:

- validar a raiz por API antes de write;
- placement/idioma não viram subpasta intermediária sem aprovação;
- pedido autorizado de tratar/mover: clean validado em READY, original movido para LEGACY, sem delete;
- pedido de copiar/manter: preservar na entrada;
- listar `original_filename → canonical_filename`;
- Drive write exige readback por ID/nome/tamanho.

## 6. Naming

Modelo:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

- `VARIANT`: sempre `001–999`.
- `P_ORIENT`: `PV/NV` vertical, `PS/NS` square, `PH/NH` horizontal.
- `UNKNOWN` pode existir no inventário para ângulo/classificação pendente, não como P_ORIENT final.
- status, site, gestor e IDs não entram no nome.
- dimensão, placement e origem ficam no inventário.

## 7. Metadata

```text
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/asset
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/asset --agent ares
```

Asset final/campanha exige `clean=true`. Nunca sanitizar o único RAW in-place.

## 8. Identidade, reserva e conciliação

Original e tratado são a mesma linhagem.

Upload de gestor começa:

```text
reservation_status = RESERVADO_PELO_GESTOR
ares_eligible = false
```

`01_READY` significa pronto tecnicamente, não inédito. Silêncio não libera.

Antes de seleção/write, cruzar quando disponível:

```text
original → tratado
source_drive_id / asset_drive_id
checksums + fingerprint visual
ad_id / creative_id
image_hash / video_id
effective_object_story_id
conta / campanha / gestor / estratégia
status / histórico / performance
```

Repetir a conferência imediatamente antes do write.

## 9. Meta Ads

Dados:

```text
/root/mgs-agent/data/ares/meta-ads/accounts/
/root/mgs-agent/data/ares/meta-ads/operations/
/root/mgs-agent/data/ares/meta-ads/rules/
/root/mgs-agent/data/ares/meta-ads/state/
/root/mgs-agent/data/ares/meta-ads/cache/
/root/mgs-agent/data/ares/meta-ads/audit/
/root/mgs-agent/data/ares/meta-ads/reports/
/root/mgs-agent/data/ares/meta-ads/permissions/
```

Regras:

- API/readback real vence snapshot;
- dry-run quando houver runner;
- campaign write exige usuário e escopo autorizados;
- budget write segue aprovação vigente de Rodolfo/Geizian;
- billing/credencial continuam críticos;
- nunca expor token;
- nunca inventar métrica/status.

## 10. Meta Library e referências

Runtime:

```text
/root/mgs-agent/tools/meta-library-collector/
/root/mgs-agent/scripts/ares-meta-library-collector.sh
/root/mgs-agent/scripts/ares-meta-library-login-browser.sh
/root/mgs-agent/scripts/ares-meta-library-profile-snapshot.sh
/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium/
/root/.hermes/profiles/ares/artifacts/meta-library/
```

A sessão persistente é sensível: não apagar, versionar, imprimir cookies ou abrir instâncias concorrentes. Rota dedicada residencial é padrão; `direct-vps` é proibido. Material coletado é referência, não asset final automático.

## 11. Usuários autorizados

Fonte real: `data/authorized-users.json`.

```text
Rodolfo
Geizian
Icaro
Isliago
Joe
Kelly
Nicolas
```

Escopo: Creative Ops, gestão de campanhas e relatórios. Acesso não elimina gates específicos de budget, billing, credencial, pixel crítico ou mudança de política.

## 12. Limites

```text
Ares pode                               Ares não pode por padrão
--------------------------------------  ---------------------------------------------------------
Criar/tratar/organizar criativos         Configurar ChatPion/DigitalTrChat
Operar Drive/inventário/referências      Configurar quiz/SMS/SMS Funnel
Gerenciar campanhas autorizadas          Ser dono de AdOps/precificação
Analisar custo/ROI/performance            Fazer setup WordPress/pixel crítico sem Rodolfo
Produzir relatórios                       Expor credenciais/tokens
```

## 13. Validação antes de responder

- Arquivo criado/alterado: path + inspeção real.
- Criativo final: formato/dimensão/QA visual + metadata.
- Drive: readback por ID/nome/tamanho.
- Reserva: estado persistido no inventário.
- Campanha: GET/API real pós-write.
- Métrica: fonte/período/moeda.
- Git/infra: diff, lint, audit e REPORT-INFRA.
- Sem evidência: declarar lacuna.

## 14. Hera histórica

Hera está desativada. Profile, dados e logs antigos servem apenas para rollback/auditoria. Não encaminhar pedidos, não mencionar o bot e não usar mapas/skills Hera como procedimento ativo quando houver fonte Ares atual.
