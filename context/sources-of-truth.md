# MGS OS — Fontes de Verdade

> Status: proposta canônica v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

Cada dado importante da MGS deve ter uma fonte oficial. Agentes podem consultar várias fontes, mas não devem inventar nem tratar prompt/memória como fonte única da empresa.

## Fontes canônicas internas

```text
Assunto                         Fonte canônica atual
------------------------------- ------------------------------------------------
Arquitetura MGS OS               context/company-os.md
Modelo operacional explicado     context/company-current-operating-model.md
Áreas oficiais                   context/areas.md
Mapa de agentes                  context/agent-map.md
Rotas                            context/routes.md
Fontes de verdade                context/sources-of-truth.md
Governança de conhecimento       context/knowledge-governance.md
Registro institucional           data/knowledge-registry.json
Candidatos ainda não canônicos   data/knowledge-inbox.jsonl
Continuidade de iniciativas      data/agent-checkpoints.json
Testes de coerência institucional data/knowledge-regression-cases.json
Permissões/matriz autoridade     context/permissions-matrix.md
Sites e verticais conceituais     context/sites.md
Config técnica de sites           data/sites.json
Equipe                           context/team.md
Permissões de usuários/agentes     data/authorized-users.json
Processos operacionais            context/processes.md
Monetização                       context/monetization.md
Aquisição                         context/acquisition.md
Segurança                         context/security-policies.md
Identidade Google Drive/Sheets    context/security-policies.md + scripts/mgs_google_workspace_auth.py + data/infra-inventory.json
Crons                             docs/CRONS.md
Pendências                        docs/PENDENCIAS.md
Audit trail                       logs/events-audit.jsonl
```

## Fontes por área

```text
Área                         Fontes principais
---------------------------- -------------------------------------------------
Executive / Management        company-os, areas, routes, audit log, pendências
Office / Follow-up             pendências, tarefas operacionais, cobranças e follow-up com gestores
Content Operations            content skills, WordPress, sites.json, processes
Creative Ops + Growth        Ares, APIs/dashboards de ads, Drive/inventário criativo, Canva, providers aprovados, UTM e performance
Revenue / AdOps               Smart Bidding, ActiveView, Discord AdOps, reports
Finance / BI                  planilha financeira, comissões, Smart Bidding, FB BM, reports
Tech / WordPress / Infra      scripts, crons, patches, Hermes, WordPress, logs
Security / Access             authorized-users, 1Password, policies, audit log
```

## Fontes externas críticas

```text
Fonte externa                  Uso operacional
------------------------------ ------------------------------------------------
Smart Bidding                   Parceiro Google/AdX/Ad Manager principal da MGS; rede e dashboard principal de gerenciamento, com sites, campanhas, ROI, blocos, tecnologia e reports.
ActiveView                      Parceiro Google/AdX/Ad Manager; exceção ativa para openzed, cliquet e subdomínios.
Facebook Business Manager       Gastos de campanha e contas de anúncio.
Google Ads                      Campanhas/aquisição quando usado.
TikTok Ads                      Canal potencial/futuro para Ares.
Google / AdX                    Camada de pagamento/monetização via parceiros.
Canva                           Organização e criação inicial de criativos.
Google Drive                     Pasta oficial de criativos; Ares lê/escreve, preserva linhagem e concilia com plataformas de campanha.
DigitalTrChat / ChatPion         Dashboard Messenger/Facebook; usuários por vertical, seguradores, páginas e bot flows.
SMS Funnel                       Envio de SMS da estratégia quiz/SMS configurada por Rodolfo.
UTM_medium                       Código de atribuição por gestor em campanhas/sites.
ChatGPT                         Apoio a criativos/conteúdo conforme escopo aprovado.
TopView.ai                      Criação de vídeos.
Grok                            Candidato futuro se testado/aprovado.
Discord AdOps                   Comunicação operacional com Smart Bidding.
Planilha financeira             Fechamento mensal e ROI consolidado.
1Password                       Credenciais e tokens; nunca expor em chat.
```

## Regra de conflito

```text
Conflito                                      Vence
-------------------------------------------- ----------------------------------
Fala recente do Rodolfo vs arquivo antigo      Fala recente do Rodolfo.
Dashboard externo validado vs arquivo antigo   Dashboard externo validado.
Permissão em memória vs authorized-users.json   authorized-users.json.
Smart Bidding vs ActiveView                    Smart Bidding como dashboard principal; ActiveView vence só nos sites ainda na tecnologia AV (`openzed`, `cliquet` e subdomínios).
Credencial em qualquer fonte vs 1Password       1Password.
Prompt de agente vs company-os/context          company-os/context.
Criativo em ferramenta vs Drive aprovado         Google Drive de criativos aprovados.
Comissão em conversa vs planilha financeira      Planilha financeira validada por Rodolfo.
Atribuição de gestor vs UTM_medium               UTM_medium da campanha/link.
Ares vs ChatPion/quiz/SMS                         Ares não configura ChatPion/DigitalTrChat, quiz ou SMS Funnel.
```

## Regra de escrita

```text
Tipo de dado                   Onde escrever
------------------------------ ------------------------------------------------
Permissões operacionais         data/authorized-users.json
Decisão/evento relevante        logs/events-audit.jsonl
Conhecimento estrutural         context/*.md
Metadados de decisão/fonte      data/knowledge-registry.json
Conhecimento ainda não aprovado data/knowledge-inbox.jsonl
Estado de iniciativa/handoff    data/agent-checkpoints.json
Casos de regressão institucional data/knowledge-regression-cases.json
Procedimento reutilizável       skills/*/SKILL.md
Automação executável            scripts/
Histórico/plano/pendência       docs/
Config técnica de sites         data/sites.json
Criativos aprovados             Google Drive de criativos aprovados
Atribuição por gestor            UTM_medium nos links/campanhas
Comissões/fechamento             Planilha financeira do Rodolfo
Credenciais                     1Password, nunca arquivos/chat
```

## Arquivos que exigem cuidado especial

```text
Fonte                           Regra
------------------------------- ------------------------------------------------
data/authorized-users.json       Não alterar sem decisão confirmada de Rodolfo.
data/sites.json                  Não alterar sem plano técnico claro.
.env / tokens / credentials      Não ler/expor no chat; uso interno controlado.
scripts/ produtivos              Validar antes/depois; manter rollback.
crons/monitores                  Evitar loops; mudança pequena e auditável.
patches/hermes/                  Não mexer sem entender impacto no runtime.
```
