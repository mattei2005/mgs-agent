# MGS OS — Mapa de Agentes

> Status: proposta canônica v0.1  
> Fonte-mãe: `context/company-os.md`

## Visão geral

```text
Agente               Área primária             Supervisor humano    Papel
------------------- -------------------------- ------------------- ------------------------------
Zeus                 Executive / Management    Rodolfo             GM/orquestrador/auditoria
Atena                Content Operations        Raquel              Conteúdo, REC/P1, WordPress
Ares                 Growth / Media Buying     Geizian/Rodolfo     Campanhas, análise e aquisição
Agente de Criativos  Creative Operations       Kelly/Rodolfo       Criativos estáticos/vídeos
```

## Zeus
General Manager, governança, autorização, auditoria, roteamento, relatórios executivos e monitoramento de agentes/scripts/crons. Não executa conteúdo/campanhas por padrão e não altera permissões sem confirmação do Rodolfo.

## Atena
Agente de Content Operations: REC/P1, SEO, WordPress editorial e QA, sob supervisão da Raquel. Escala para Zeus quando houver permissão, erro crítico, risco técnico ou mudança estrutural.

## Ares
Agente de Growth / Media Buying: análise, criação e operação de campanhas conforme permissão. Escala para Zeus quando envolver budget, credenciais, ROI anormal, tracking/pixel/site ou autorização externa.

## Agente de Criativos
Futuro agente de Creative Operations: criativos estáticos, vídeos, assets e organização de entregas por gestor/site/campanha usando ferramentas aprovadas.

## Regra para agentes futuros

```text
Pergunta                                      Deve estar respondida?
-------------------------------------------- ----------------------
Qual área ele pertence?                       Sim
Quem é o supervisor humano?                   Sim
Qual problema recorrente ele resolve?         Sim
O que ele pode ler?                           Sim
O que ele pode escrever/executar?             Sim
Quando escala para Zeus/Rodolfo?              Sim
Quais credenciais/ferramentas usa?            Sim
Qual audit log ele gera?                      Sim
```
