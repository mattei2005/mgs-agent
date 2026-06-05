# MGS OS — Fontes de Verdade

> Status: proposta canônica v0.1  
> Fonte-mãe: `context/company-os.md`

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
Permissões/matriz autoridade      context/permissions-matrix.md
Sites e verticais conceituais     context/sites.md
Config técnica de sites           data/sites.json
Equipe                           context/team.md
Permissões de usuários/agentes     data/authorized-users.json
Processos operacionais            context/processes.md
Monetização                       context/monetization.md
Aquisição                         context/acquisition.md
Segurança                         context/security-policies.md
Crons                             docs/CRONS.md
Pendências                        docs/PENDENCIAS.md
Audit trail                       logs/events-audit.jsonl
```

## Fontes por área

```text
Área                         Fontes principais
---------------------------- -------------------------------------------------
Executive / Management        company-os, areas, routes, audit log, pendências
Content Operations            content skills, WordPress, sites.json, processes
Growth / Media Buying         dashboards de ads, Smart Bidding, planilhas, Ares
Creative Operations           Canva, ChatGPT, TopView.ai, pastas dos gestores
Revenue / AdOps               Smart Bidding, ActiveView, Discord AdOps, reports
Finance / BI                  planilha financeira, Smart Bidding, FB BM, reports
Tech / WordPress / Infra      scripts, crons, patches, Hermes, WordPress, logs
Security / Access             authorized-users, 1Password, policies, audit log
```

## Fontes externas críticas
Smart Bidding, ActiveView, Facebook Business Manager, Google Ads, Google/AdX, Canva, ChatGPT, TopView.ai, Discord AdOps, planilha financeira e 1Password.

## Regra de conflito
Fala recente do Rodolfo vence arquivo antigo; dashboard externo validado vence arquivo antigo; `authorized-users.json` vence memória; Smart Bidding vence ActiveView exceto `openzed`, `cliquet` e subdomínios; credenciais vêm do 1Password e nunca são expostas.
