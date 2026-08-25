---
name: meta-ads-intraday-operations
description: "Use em governança, relatórios e crons Meta por operação."
version: 3.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, intraday, daily, campaigns, reporting, growth, mgs]
---

# Meta Ads Intraday Operations — Ares/MGS

Use esta skill para estruturar, revisar ou manter leitura intraday, relatório diário, guardrails e crons Meta Ads do Ares. Ela é uma camada **genérica de governança**: métricas, thresholds, horários, budgets, threads e ações pertencem ao contrato específico de cada operação.

## Disclosure progressivo

1. Identifique a operação, a conta e o pedido exato.
2. Abra primeiro o arquivo vivo em `/root/mgs-agent/data/ares/meta-ads/operations/` e a conta em `accounts/`.
3. Carregue a skill específica da estratégia/operação, quando existir.
4. Para layout de relatório, abra `references/current-reporting-contract.md`.
5. Para falhas conhecidas, abra `references/current-operational-pitfalls.md`.
6. Evidência histórica nunca vira regra ativa por semelhança.

## Contrato obrigatório por operação

Antes de criar cron ou executar write, o contrato deve definir explicitamente:

```text
Campo                         Obrigatório
----------------------------  -------------------------------------------------
operation_id                  site, país, vertical, idioma e estratégia
account_id / alias            conta real validada por API
currency / timezone           readback da Meta
owner / manager               pessoas autorizadas e gates de budget
objective / optimization      objetivo, evento e fonte da métrica
campaign structure            budget level, adsets, ads, bid strategy
report metrics                fórmula, período, moeda e fonte
Intraday / Daily schedule     horários no timezone da conta
fixed Discord threads         destino por tipo de relatório/operação
write mode                    read_only, dry_run ou controlled_write
creative policy               reserva, Drive × Meta e elegibilidade
recovery / rollback           proveniência e readback pós-write
```

Campos ausentes ficam `pending_review` e bloqueiam somente a ação dependente. Nunca preencher usando contrato de outra operação.

## Modos

```text
Modo                Comportamento
------------------  ------------------------------------------------------------
read_only           Consulta API/config e salva evidência; zero write.
dry_run             Calcula ações sem alterar a Meta.
recommend           Recomenda e aguarda a autorização aplicável.
controlled_write    Executa somente o escopo pontual e pré-aprovado.
autonomous_guarded  Exige política própria, allowlist, limites e aprovação formal.
```

## Governança consolidada

- Runtime/API/dados reais vencem snapshots para estado atual.
- MGS OS, `authorized-users.json` e `permissions-matrix.md` vencem para dono e autoridade.
- Token vem do item 1Password registrado na conta; nunca existe token global implícito e nunca é impresso.
- Scripts usam `ares-meta-common.py` para cache protegido, throttle, headers de quota e backoff limitado.
- Toda resposta GET/POST/batch alimenta o estado de quota quando os headers existirem.
- Erros de validação, parâmetro ou compliance não recebem retry cego.
- Antes de correção, reconciliar efeitos parciais e reutilizar o request/IDs persistidos; nunca repetir POST não idempotente às cegas.
- Sucesso de write exige GET/readback do alvo completo e audit com estado anterior/posterior.
- Pausar, reativar, criar, clonar ou editar exige o modo autorizado no contrato da operação.
- Budget segue o gate explícito vigente; billing, credencial, pixel/CAPI e app/permissão continuam críticos.
- Campanha nova deve nascer PAUSED, salvo autorização operacional explícita em contrato validado.
- IDs técnicos ficam em audit; relatório humano mostra alias e nomes operacionais.

## Métricas e decisão

- Cada operação declara a métrica principal e sua fórmula. Não assumir `subs`, `MO`, `CPMO`, `CPS`, purchase ROAS ou ROI por país/estratégia.
- Toda métrica reportada informa período, moeda, fonte e limitação relevante.
- Antes de atribuir queda à campanha, checar anomalia de monetização, entrega e fonte de receita quando o contrato exigir reconciliação externa.
- Calibração inicial deve começar read-only/dry-run e comparar API com conferência manual do gestor antes de liberar automação.
- Learning, carência, persistência e exceções de bid strategy são parâmetros do contrato, não defaults globais.

## Crons e Discord

- Crons operacionais determinísticos usam `script` + `no_agent=true`.
- Em Discord operacional, preferir `deliver=local` quando o wrapper publica diretamente; stdout vazio evita duplicidade.
- Não usar cron com agente e `deliver=origin/all` para conclusão diferida pós-restart.
- O wrapper deve ficar abaixo do timeout do scheduler e transformar timeout/rate-limit em mensagem sanitizada + audit local.
- Threads fixas são registradas no contrato da operação. Nunca criar thread nova quando houver rota fixa aplicável.
- Intraday, Diário, criação e incidentes permanecem separados quando o contrato assim definir.
- Sem ação/erro, o cron fica silencioso, exceto relatório periódico explicitamente configurado.
- Alteração de cron exige readback `enabled/state/schedule/script/deliver/no_agent` e REPORT-INFRA.

## Onboarding de nova operação

1. Validar solicitante e autoridade.
2. Validar token e conta por API read-only sem expor segredo.
3. Criar `accounts/<account_id>.json` com referência 1Password e readback Meta.
4. Criar `operations/<operation_id>.json` inicialmente com `write_enabled=false`.
5. Registrar gestores, aliases e threads fixas.
6. Fechar objetivo, estrutura, naming, métricas, budgets e horários com o dono.
7. Criar skill específica da estratégia/operação somente após o contrato mínimo.
8. Implementar runner e wrappers determinísticos com testes.
9. Criar crons apenas em read-only/dry-run e validar entrega.
10. Liberar controlled-write ou autonomia somente por decisão explícita e readback.

## Operação Eggbev em revisão

O contrato em elaboração está em:

```text
/root/mgs-agent/data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json
/root/mgs-agent/data/ares/meta-ads/accounts/1034081997659047.json
```

Enquanto houver campos `pending_review`, não criar crons Eggbev nem herdar regras de tráfego direto ou de outra operação. A skill específica planejada é `eggbev-us-cc-en-bot-operations`.

## Segurança e autoridade

- Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e Nicolas podem operar Ares conforme o registry real.
- A autorização de Campaign Ops não libera automaticamente budget, billing, credencial ou produção fora do playbook.
- Nunca expor token, senha, cookie, payment data ou chave.
- Mudança de estratégia, exclusão permanente, billing ou ampliação de escopo exige o gate próprio.

## Referências atuais

- Layout de relatórios: `references/current-reporting-contract.md`
- Pitfalls operacionais: `references/current-operational-pitfalls.md`
- Histórico removido das rotas ativas permanece somente no Git/audit e não deve ser carregado como procedimento.
