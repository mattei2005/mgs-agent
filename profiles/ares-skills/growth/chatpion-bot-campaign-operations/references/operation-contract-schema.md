# Schema do contrato por operação

Cada consumidor da família `chatpion_bot_messenger` mantém identidade e valores fora da skill principal.

## Campos obrigatórios

- `operation_id`, site/domínio, país, vertical e idioma;
- alias e caminho da conta Meta;
- moeda, timezone, owners e autoridade;
- `strategy_binding.family_id` e versão mínima;
- contrato Engine e `supported_modes`;
- Page/UTM/PBIA, evento, pixel e JSON aplicáveis;
- estrutura, copy, criativos e naming;
- thresholds, comparadores, fases, horários e budgets;
- guardrails, holds, freshness e ações permitidas;
- routes, prompts, runners, states, audits e crons;
- flags de write e activation.

## Proibido herdar

Credenciais, billing, IDs técnicos da fonte, campaigns, media IDs, Pages, states, denylist, baselines, performance, request IDs, locks, schedules e autoridade operation-scoped.

## Cadastro parcial e aceite fail-closed

Use este ramo quando o onboarding estiver autorizado, mas a identidade do anunciante ou outra dependência ainda não estiver comprovada. Ele registra progresso; não é uma rota alternativa de publicação.

1. Preserve o request original e registre no contrato a autoridade por conta, solicitante, ações permitidas, origem verificável, exclusões e controles. Mantenha a autoridade ativa separada dos campos técnicos pendentes; uma pendência de capacidade não revoga a aprovação humana.
2. Consulte a conta exata e a hierarquia da fonte em read-only pelo helper canônico. Valide Business, moeda, timezone, paginação e identidade da Page; derive contagens/estados em código. Persista somente dados sanitizados, nunca Page Access Token.
3. Cadastre somente o que foi comprovado. Mantenha `token_item=null` quando o anunciante correto não estiver resolvido, `supported_modes=[]`, flags de write/activation desabilitadas e o consumidor em `onboarding_candidates`, não em `consumers` ativos. Não preencha capacidades de outra conta para satisfazer o schema.
4. Exerça `ares_campaign_v3.schema.Manifest.from_dict` e `ares_campaign_v3.prevalidation.validate_account_policy` em uma verificação offline, sem transporte nem execute, para provar que a conta incompleta é recusada. Com exigência de modos explícitos, a lista vazia é rejeitada antes da análise do modo; teste o primeiro gate real, sem enfraquecê-lo para obter outra mensagem. Um payload usado apenas nesse teste nunca vira manifest de produção nem prova aceite Meta.
5. Compare a configuração com o backup e confirme que somente a entrada da conta nova foi acrescentada e que os consumidores ativos anteriores não mudaram. Registre separadamente teste fail-closed aprovado e onboarding ainda incompleto.
6. Se o acesso à Page não estiver comprovado, preserve o erro real e peça somente a informação não recuperável, como o perfil anunciante que a tem vinculada. Não conclua ausência de scope a partir de `code=10`, nem adote outro anunciante ou System User como fallback. Alteração de credencial ou delegação de ativo exige autorização própria.
7. Atualize checkpoint, inventário e registro canônico com causa e próxima ação exatas. Quando a dependência for resolvida, revalide e promova a mesma conta/request; não repita autorização já registrada nem interprete a promoção como aprovação de campanha ou automação.

## Regra de override

O contrato de família define o mecanismo e os campos exigidos. O contrato da operação fornece valores e exceções. Ausência não significa usar o valor de outro consumidor; significa falhar fechado.
