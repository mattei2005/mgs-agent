# MGS OS — Mapa Operacional

> Status: proposta canônica v0.1  
> Dono executivo: Rodolfo Mattei  
> Orquestração: Zeus  
> Função: índice rápido para localizar a fonte certa antes de usar busca ampla.

## 1. Como usar este mapa

Este arquivo é o mapa-mãe de navegação do Zeus dentro do MGS OS.

Regra prática:

- Primeiro identificar o assunto da pergunta.
- Depois abrir a fonte indicada neste mapa.
- Usar `search_files` só como fallback quando o arquivo certo não estiver claro, quando houver termo desconhecido ou quando for necessário procurar drift/inconsistência.

## 2. Fontes de entrada rápidas

- Estrutura da empresa: `context/company-os.md`
- Áreas oficiais: `context/areas.md`
- Agentes: `context/agent-map.md`
- Mapa operacional Ares: `context/ares-operational-map.md`
- Rotas/handoffs: `context/routes.md`
- Fontes de verdade: `context/sources-of-truth.md`
- Governança de conhecimento: `context/knowledge-governance.md`
- Registro institucional: `data/knowledge-registry.json`
- Candidatos de conhecimento: `data/knowledge-inbox.jsonl`
- Checkpoints de iniciativas: `data/agent-checkpoints.json`
- Regressão de conhecimento: `data/knowledge-regression-cases.json`
- Permissões conceituais: `context/permissions-matrix.md`
- Pessoas/equipe: `context/team.md`
- Sites conceituais: `context/sites.md`
- Sites técnicos: `data/sites.json`
- Crons documentados: `docs/CRONS.md`
- Inventário de estrutura: `docs/mgs-structure-inventory.md`
- Audit log MGS: `logs/events-audit.jsonl`

## 3. Mapa por área

### Executive / Management

- Donos: Rodolfo + Geizian
- Agente: Zeus
- Abrir primeiro:
  - `context/company-os.md`
  - `context/areas.md`
  - `context/team.md`
  - `context/routes.md`
- Usar para:
  - estratégia
  - prioridade
  - organograma
  - governança
  - conflito entre áreas
  - criação/limite de agentes

### Office / Follow-up

- Dona: Ially
- Agente dedicado: nenhum hoje
- Abrir primeiro:
  - `context/areas.md`
  - `context/team.md`
  - `docs/PENDENCIAS.md`
- Usar para:
  - cobrança de tarefas
  - follow-up com gestores
  - pendências operacionais

### Content Operations

- Dona: Raquel
- Agente: Atena
- Abrir primeiro:
  - `context/routes.md`
  - `context/agent-map.md`
  - `profiles/atena-soul.md`
  - `skills/content-generate-rec-p1/`
  - `skills/content-publish-wordpress/`
- Runtime/dados:
  - `/root/.hermes/profiles/atena/logs/`
  - `data/sites.json`
  - `data/article-tracker.db`
  - `data/card-cache.db`
- Usar para:
  - REC/P1
  - artigo SEO
  - WordPress editorial
  - publicação
  - Yoast
  - QA editorial

### Creative Operations + Growth / Media Buying

- Donos: Rodolfo + Geizian + Kelly + gestores autorizados
- Agente: Ares
- Abrir primeiro:
  - `context/ares-operational-map.md`
  - `context/acquisition.md`
  - `context/routes.md`
  - `context/agent-map.md`
  - `profiles/ares-soul.md`
- Runtime/dados:
  - `/root/.hermes/profiles/ares/logs/`
  - `data/ares/meta-ads/`
  - `data/ares/creative-ops/`
  - `scripts/ares-*.py`
  - `logs/ares-*.log`
  - Shared Drive canônico `MGS-AGENTS`: `https://drive.google.com/drive/folders/0AEwt4Ye690ocUk9PVA`
  - Evidência do cutover integral: `data/ares/creative-ops/shared-drive-migration/20260716T003345Z/`
- Usar para:
  - brief, copy, imagem e vídeo
  - referências Meta Library/YouTube
  - sanitização, naming, Drive e inventário
  - reserva/elegibilidade e conciliação Meta × Drive
  - campanhas Facebook/Google e futuros canais aprovados
  - custo, ROI, tracking por gestor e relatórios
- Limites:
  - Ares não configura ChatPion/DigitalTrChat.
  - Ares não configura quiz/SMS Funnel.
  - Ares não é dono de AdOps/precificação.
  - Ares não faz setup WordPress/pixel crítico sem Rodolfo.
  - Budget write segue gates de Rodolfo/Geizian.
  - Operações usam exclusivamente o Shared Drive canônico `MGS-AGENTS`, administrado no Google Workspace por `support@matteiservicesinc.com`.

### Revenue / AdOps

- Donos: Rodolfo + Geizian + gestores
- Agente executor dedicado: nenhum hoje
- Zeus: reporta/apoia
- Abrir primeiro:
  - `context/monetization.md`
  - `context/sources-of-truth.md`
  - `context/routes.md`
- Usar para:
  - Smart Bidding
  - ActiveView
  - AdX/AdManager
  - blocos
  - aprovação de site
  - precificação
  - regras de anúncio

### Finance / BI

- Dono: Rodolfo
- Agente: Zeus como report
- Abrir primeiro:
  - `context/company-os.md`
  - `context/areas.md`
  - `context/sources-of-truth.md`
- Fontes externas reais:
  - planilha financeira do Rodolfo
  - Smart Bidding
  - ActiveView
  - Facebook Business Manager
- Usar para:
  - fechamento mensal
  - custo
  - receita
  - comissão
  - salário
  - ROI consolidado
  - tráfego inválido

### Tech / WordPress / Infra

- Dono: Rodolfo + Zeus/Tech
- Agente: Zeus
- Abrir primeiro:
  - `docs/CRONS.md`
  - `docs/mgs-structure-inventory.md`
  - `scripts/`
  - `patches/`
  - `profiles/`
  - `/root/.hermes/profiles/`
- Runtime:
  - `logs/`
  - systemd
  - crontab
  - `data/*-state.json`
- Usar para:
  - Hermes
  - gateway
  - VPS
  - systemd
  - cron
  - scripts
  - patches
  - WordPress técnico
  - plugins
  - pixels

### Security / Access

- Dono: Rodolfo + Zeus
- Abrir primeiro:
  - `context/security-policies.md`
  - `context/permissions-matrix.md`
  - `data/authorized-users.json`
  - `logs/events-audit.jsonl`
- Fonte externa:
  - 1Password
- Usar para:
  - autorização de usuário
  - permissão real
  - token
  - credencial
  - dashboard externo
  - risco
- Regra:
  - Nunca expor credenciais em chat.
  - Alterar `authorized-users.json` só com confirmação do Rodolfo.

## 4. Mapa por agente

### Zeus

- Área: Executive / Ops
- Vivo:
  - `/root/.hermes/profiles/zeus/SOUL.md`
  - `/root/.hermes/profiles/zeus/config.yaml`
  - `/root/.hermes/profiles/zeus/logs/`
  - `/root/.hermes/profiles/zeus/sessions/`
- Versionado:
  - `profiles/zeus-soul.md`
  - `profiles/zeus-config.yaml`
  - `profiles/zeus-skills/`
- Usa principalmente:
  - `context/company-os.md`
  - `context/agent-map.md`
  - `context/routes.md`
  - `context/sources-of-truth.md`
  - `context/permissions-matrix.md`

### Atena

- Área: Content Operations
- Vivo:
  - `/root/.hermes/profiles/atena/SOUL.md`
  - `/root/.hermes/profiles/atena/config.yaml`
  - `/root/.hermes/profiles/atena/logs/`
- Versionado:
  - `profiles/atena-soul.md`
  - `profiles/atena-config.yaml`
  - `profiles/atena-skills/`
- Usa principalmente:
  - `skills/content-generate-rec-p1/`
  - `skills/content-publish-wordpress/`
  - `data/sites.json`

### Ares

- Área: Creative Operations + Growth / Media Buying
- Vivo:
  - `/root/.hermes/profiles/ares/SOUL.md`
  - `/root/.hermes/profiles/ares/config.yaml`
  - `/root/.hermes/profiles/ares/logs/`
  - `/root/.hermes/profiles/ares/skills/growth/`
- Versionado:
  - `profiles/ares-soul.md`
  - `profiles/ares-config.yaml`
  - `profiles/ares-skills/growth/`
- Usa principalmente:
  - `context/ares-operational-map.md`
  - `context/acquisition.md`
  - `context/routes.md`
  - `data/ares/meta-ads/`
  - `data/ares/creative-ops/`
  - `scripts/ares-*.py`
- Regra HOT:
  - Antes de busca ampla para `drive`, `campaign`, `meta`, `creative`, `UPLOAD`, `reference`, `video`, `budget` ou `roi`, abrir `context/ares-operational-map.md`.

## 5. Mapa por pasta

### `context/`

- Classe: canônico/conceitual
- Usar para entender a empresa, áreas, agentes, rotas, fontes, permissões, sites, equipe e políticas.
- Risco: baixo para leitura; médio para edição.

### `data/`

- Classe: runtime/estado
- Usar para fatos operacionais, permissões reais, configuração técnica de sites, caches, DBs e estados de monitores.
- Risco: alto.

### `docs/`

- Classe: documentação/plano/histórico
- Usar para planos, inventários, crons documentados, pendências, changelog e decisões históricas.
- Risco: baixo/médio.

### `scripts/`

- Classe: automação produtiva
- Usar para execução, validação, crons, pipelines, monitores e wrappers.
- Risco: alto.

### `profiles/`

- Classe: versão controlada dos agentes
- Usar para revisar SOUL/config/skills versionados e comparar com runtime vivo.
- Risco: médio/alto.

### `/root/.hermes/profiles/`

- Classe: runtime vivo Hermes
- Usar para estado real dos agentes, logs vivos, config viva, gateway, sessões, memória e auth.
- Risco: crítico.

### `logs/`

- Classe: logs/audit
- Usar para investigação, validação de execução e audit trail.
- Regra: consulta/append-only; não editar manualmente.

### `patches/`

- Classe: patch local Hermes/MGS
- Usar para updates Hermes, patch guard e comportamento customizado.
- Risco: crítico.

### `backups/`

- Classe: backup/snapshot
- Usar para rollback e comparação pré/pós alteração.
- Regra: preservar último backup válido por família.

### `tools/`

- Classe: ferramenta auxiliar
- Usar para automações auxiliares, principalmente Creative/Canva.

### `experiments/`

- Classe: experimento/spike
- Usar para Honcho e provas de conceito.
- Regra: não tratar como fonte de verdade.

## 6. Pergunta → primeira fonte

- “Como está a empresa?” → `context/company-os.md`, `context/areas.md`, `context/team.md`
- “Quem faz o quê?” → `context/agent-map.md`, `context/areas.md`, `context/routes.md`
- “Qual agente cuida disso?” → `context/agent-map.md`, `context/routes.md`
- “Quem pode autorizar?” → `context/permissions-matrix.md`, depois `data/authorized-users.json` se for permissão real
- “Esse usuário pode pedir conteúdo?” → `data/authorized-users.json`, depois `logs/events-audit.jsonl` se precisar histórico
- “Onde está um site?” → `context/sites.md` para conceito; `data/sites.json` para técnico
- “Qual site/pixel/config WordPress?” → `data/sites.json`
- “Atena fez X?” → `/root/.hermes/profiles/atena/logs/`, `data/article-tracker.db`, WordPress/API se necessário
- “Ares fez X?” → `/root/.hermes/profiles/ares/logs/`, `scripts/ares-*.py`, `data/ares/`, `logs/ares-*.log`
- “Tem erro no Hermes/VPS?” → `/root/.hermes/profiles/*/logs/errors.log`, systemd, journalctl filtrado, `docs/CRONS.md`, `data/*-state.json`
- “Cron está ativo?” → `docs/CRONS.md`, crontab real, logs do script, estado do monitor
- “Já decidimos isso?” → `data/knowledge-registry.json`, depois a `canonical_source` do registro
- “Onde paramos nessa iniciativa?” → `data/agent-checkpoints.json`, depois a thread/source indicada
- “Essa informação nova já é canônica?” → `data/knowledge-inbox.jsonl` para candidato; `data/knowledge-registry.json` para promovido
- “As rotas e decisões críticas continuam coerentes?” → `scripts/mgs-knowledge-control.py regression` com `data/knowledge-regression-cases.json`
- “Isso está no Git?” → `git status`, `git log`, `git diff`, `logs/auto-push.log`
- “Honcho está como quê?” → `scripts/mgs-memory-copilot`, `experiments/honcho-spike/mgs_memory_copilot.py`, `experiments/honcho-spike/README.md`, SOUL dos agentes

## 7. Mapa de risco

- Baixo risco leitura: `context/`, `docs/`, `reports/`, `experiments/`, `tools/`
- Médio risco: `profiles/`, `skills/`, `backups/`, `tmp/`, staging
- Alto risco: `data/`, `scripts/`, `api/`, crons, systemd, logs se editados
- Crítico: `.env`, `.secrets/`, `auth.json`, 1Password, `data/authorized-users.json`, `data/sites.json`, `patches/hermes/`, `/root/.hermes/profiles/*`

## 8. Política de anexos e exibição no Discord

- Se Rodolfo pedir “por aqui”, “no chat” ou apenas pedir explicação, responder inline.
- Só enviar arquivo/anexo quando Rodolfo pedir explicitamente arquivo ou anexo.
- Para documentos longos, primeiro oferecer resumo inline e perguntar se ele quer anexo.
