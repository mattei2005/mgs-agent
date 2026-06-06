# MGS OS — Mapa de Agentes

> Status: proposta canônica v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Visão geral

```text
Agente               Área primária             Supervisor humano    Papel
------------------- -------------------------- ------------------- ------------------------------
Zeus                 Executive / Management    Rodolfo             GM, orquestração, auditoria.
Atena                Content Operations        Raquel              Conteúdo, REC/P1, WordPress.
Ares                 Growth / Media Buying     Geizian/Rodolfo     Campanhas, análise e aquisição.
Kelly                Creative Operations       Kelly/Rodolfo       Criativos estáticos/vídeos.
Futuros agentes      Área específica           Dono definido        Só com escopo e permissão.
```

## Zeus

General Manager da MGS quando Rodolfo não está: governança, autorização, auditoria, roteamento, relatórios executivos, monitoramento de agentes/scripts/crons e alertas críticos.

Limites:

- não executa produção de conteúdo por padrão;
- não sobe campanha por padrão;
- não altera permissões sem confirmação do Rodolfo;
- não expõe credenciais;
- não move/remove estrutura produtiva sem aprovação.

## Atena

Agente de Content Operations: REC/P1, SEO, WordPress editorial, QA e rotina de publicação, sob supervisão da Raquel.

Escala para Zeus quando houver:

- usuário externo não autorizado;
- erro crítico ou recorrente;
- risco técnico em WordPress/publicação;
- pedido fora do playbook;
- conflito de prioridade;
- mudança estrutural.

## Ares

Agente planejado de Growth / Media Buying: análise, criação e operação de campanhas conforme permissão aprovada.

Escala para Zeus/Rodolfo quando envolver:

- budget;
- credenciais;
- ROI anormal;
- tracking/pixel/site;
- dashboard externo;
- autorização externa;
- risco financeiro/reputacional.

## Kelly — agente de criativos

Futuro agente de Creative Operations: criativos estáticos, vídeos, assets e organização de entregas por gestor/site/campanha usando ferramentas aprovadas.

Escopo inicial provável:

```text
Entrada   Pedido de criativo por site/campanha/vertical.
Processo  Gerar/organizar assets em ferramenta aprovada.
Saída     Criativo entregue ao gestor no formato/local combinado.
Controle  Kelly/Rodolfo aprovam ferramentas e padrões.
```

## Regra para agentes futuros

Nenhum agente novo nasce só porque existe ferramenta disponível. Ele nasce quando a empresa tem área, problema recorrente, dono humano, fonte de verdade e permissão clara.

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
Como validar que não quebrou a operação?      Sim
```
