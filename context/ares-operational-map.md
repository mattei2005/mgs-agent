# Ares — Mapa Operacional HOT

> Status: operacional v0.4
> Dono executivo: Rodolfo Mattei
> Agente: Ares
> Área: Creative Operations + Growth / Media Buying
> Atualização: Shared Drive `MGS-AGENTS` canônico e cutover integral validados em 2026-07-15/16.

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
Executor Campaign Ops v3                meta-campaign-engine-v3/SKILL.md
Meta intraday + governança consolidada    meta-ads-intraday-operations/SKILL.md
Redirect histórico de guardrails          meta-ads-governance-guardrails/SKILL.md
Tráfego direto CBO/UTM                  direct-traffic-cbo-operations/SKILL.md
Sanitizador metadata                    /root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
Dados criativos                         /root/mgs-agent/data/ares/creative-ops/
Inventário unificado                    /root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl
Intake Drive read-only                  /root/mgs-agent/scripts/ares-drive-upload-manual-inventory.py
Dados Meta Ads                          /root/mgs-agent/data/ares/meta-ads/
Scripts Ares                            /root/mgs-agent/scripts/ares-*
Logs Ares                               /root/.hermes/profiles/ares/logs/
Audit MGS                               /root/mgs-agent/logs/events-audit.jsonl
```

### Canais Discord canônicos

```text
Canal                              ID                    Participantes                         Finalidade
---------------------------------  --------------------  ------------------------------------  ----------------------------------------------
ares-diretoria                     1508853425952133180   Rodolfo, Zeus e Ares                  Diretoria privada e histórico completo do Ares
ares-criativos                     1516887105543077949   Rodolfo, Zeus, Ares e gestores        Creative Ops: brief, referência, upload, Drive e inventário
eggbev-us-cc-en-01-g006            1539422731727147079   Rodolfo, Nicolas, Zeus e Ares         Eggbev US-CC-EN BOT: regras, campanhas e relatórios
ares-creditoparaveiculo-br-car-br  1539432300364824607   Rodolfo, Nicolas, Geizian, Zeus e Ares creditoparaveiculo.com BR-CAR-BR: tráfego direto
```

`ares-diretoria` é o canal principal/home do profile. `ares-criativos` é o canal compartilhado de Creative Ops e não recebe novas rotas de Campaign Ops. Os canais privados por operação usam múltiplas contas por alias e threads separadas para criação, relatórios e criativos. Rodolfo (`344196393512075265`) e Zeus (`1496296175014252634`) são membros obrigatórios de toda thread criada pelo Ares em qualquer canal pai, inclusive Diretoria e canais futuros; listas por canal são aditivas. Assim, toda thread iniciada por Nicolas dentro das rotas do Ares inclui Rodolfo automaticamente. `eggbev-us-cc-en-01-g006` cobre a estratégia BOT/Messenger Eggbev US-CC-EN, é gerida por Rodolfo e Nicolas e também auto-adiciona Nicolas (`1055570806945620030`). Threads fixas: regras `1543280854024060999`, Intraday `1541578606076231750`, Diário `1541578596253175858`, criar campanhas `1541578556037927053`, clonar campanhas `1543333373945053184` e limite de leads `1543312825890381865`. A antiga thread de regras `1541578622106865815` está supersedida e não recebe novas regras ativas. Regras de operações anteriores e de tráfego direto não são herdadas automaticamente. `ares-creditoparaveiculo-br-car-br` cobre creditoparaveiculo.com BR-CAR-BR na estratégia de tráfego direto e também auto-adiciona Nicolas e Geizian (`321263240782807040`) em toda thread nova. Nenhum outro canal Discord é rota ativa do Ares.

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
"criar/clonar/lote/alta escala Meta"             meta-campaign-engine-v3
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

Creative Ops e Campaign Ops compartilham o mesmo estado no Ares.

## 5. Intake e Drive

Raiz operacional atual validada por API/readback:

```text
Shared Drive: MGS-AGENTS
ID: 0AEwt4Ye690ocUk9PVA
URL: https://drive.google.com/drive/folders/0AEwt4Ye690ocUk9PVA
```

Esta é a única raiz operacional. O Workspace é administrado por `support@matteiservicesinc.com`; nomes, caminhos e estrutura permanecem iguais aos validados no cutover.

```text
MGS-AGENTS/CRIATIVOS/
├── UPLOAD MANUAL      # fila temporária, inclusive arquivos >10 MB
├── GEIZIAN            # cópias para upload do gestor; ignorar no pool canônico
├── LIBRARY META       # referências; nunca asset final automático
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

Modelo, com subtipo veicular opcional para a vertical `CAR`:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_[MOTO_]_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

- `VARIANT`: sempre `001–999`.
- `P_ORIENT`: somente `PV/NV` vertical e `PH/NH` square/feed 1:1 ou horizontal; `PS/NS` não entram em nomes finais.
- `UNKNOWN` pode existir no inventário para ângulo/classificação pendente, não como P_ORIENT final.
- status, site, gestor e IDs não entram no nome.
- dimensão, placement e origem ficam no inventário.
- idioma `BR` significa português do Brasil e é o padrão quando país=BR e o pedido diz apenas “Português”; `PT` significa português de Portugal explícito.
- Para `CAR`, revisar cada imagem/timeline real e registrar `vehicle_type=MOTO|CARRO`. Moto usa `MOTO` imediatamente após `FORMAT`; carro mantém o nome sem token adicional. A decisão é por asset, inclusive em lote misto.

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
/root/mgs-agent/data/ares/meta-ads/engine-v3/
/root/mgs-agent/scripts/ares-campaign-engine-v3.py
```

Criação/clonagem nova começa em `meta-campaign-engine-v3`, nunca por busca ampla em `scripts/ares-*`. O executor v3 está ativo sob guards de `development_access`; v2 é somente rollback. Mídia é pre-stageada, bundles têm duas campanhas por conta, lanes são independentes e o readback é um outer batch por bundle.

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

Escopo: todos os usuários listados podem operar Creative Ops e Campaign Ops. Kelly também é gestora de campanhas; Geizian está autorizado nos dois módulos. Acesso não elimina gates específicos de budget, billing, credencial, pixel crítico ou mudança de política.

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


