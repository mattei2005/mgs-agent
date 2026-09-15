---
name: direct-traffic-shein-operations
description: Use quando Ares operar tráfego direto SHEIN nos EUA.
version: 0.2.3
author: Rodolfo Mattei, Hermes Agent
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, ares, shein, direct-traffic, meta-ads, campaign-ops]
    related_skills: [paid-acquisition-operations, creative-operations-mgs, creative-taxonomy-mgs, meta-campaign-engine-v3]
---

# Direct Traffic SHEIN Operations — MGS/Ares

Skill específica da vertical SHEIN em tráfego direto Meta para os Estados Unidos. Ela isola o segmento SHEIN das regras operacionais de financiamento veicular: ambos usam tráfego direto, mas não compartilham contas, nomes, eventos, bids, budgets, schedules, learning policy, relatórios, criativos ou automações.

## Quando usar

Carregue esta skill quando o pedido vier de um canal `shein-g001`…`shein-g006` ou mencionar simultaneamente SHEIN, Meta e tráfego direto nos EUA.

Não use `direct-traffic-cbo-operations` como fonte única da operação SHEIN. Essa skill mantém mecanismos genéricos e regras específicas de outras operações, inclusive Creditoparaveiculo; nenhum valor ou lifecycle veicular é herdado.

## Fontes obrigatórias

1. Contrato vivo da operação: `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json`.
2. Conta Meta: runtime/API real e registro account-scoped criado após o primeiro readback.
3. Criativos: `data/ares/creative-ops/inventory/assets.jsonl` + Shared Drive `MGS-AGENTS`.
4. Autoridade: `data/authorized-users.json` e `context/permissions-matrix.md`.
5. Criação/clone/lote: skill `meta-campaign-engine-v3` e seu executor central.
6. Contrato v3 da operação: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-v3.json`.
7. Adapter/runner determinístico: `ares_campaign_v3.shein` + `scripts/ares-shein-campaigns.py`.

O Engine v3 contém apenas mecânica universal de campanha. SHEIN materializa naming, UTMs, prova social, payload Graph v26, fontes, criativos e pós-processamento no adapter/runner próprio; relatórios e estratégia não entram no executor. Não criar v4 nem um campaign writer paralelo para separar nichos.

Conclusão: contrato, gestor/canal e conta alvo estão reconciliados antes de interpretar valores históricos como vigentes.

## Identidade da operação

Resolver sites, idiomas, gestores, canais e authority sempre no contrato vivo. O desenho vigente permite ao mesmo gestor operar simultaneamente os sites EN e ES, mas mantém contas e perfis anunciantes isolados por canal/gestor.

Regras:

- site EN exige campanha/copy/criativo compatível com EN;
- site ES exige campanha/copy/criativo compatível com ES;
- uma conta ou perfil de outro gestor nunca é fallback;
- canal preparado não prova que uma conta já foi onboardada;
- Pages SHEIN autorizadas podem estar atribuídas no Business Manager; isso não substitui GET ao vivo da Page, tarefas e identidade antes do write;
- toda conta recebe alias curto somente depois de GET Meta de nome, moeda, timezone, acesso e saúde.

Conclusão: nenhum write depende de conta, perfil ou idioma inferido por semelhança.

## Fase de rollout atual

A fase vigente é `PHASE_1_CAMPAIGN_CREATION_ONLY`: gestores praticam criação do zero, duplicação e clone. Não há thread fixa; as seis threads de criação abertas no onboarding foram excluídas por pedido de Rodolfo e validadas como ausentes.

- Não criar Diário, Intraday/Otimização, Criativos ou crons nesta fase.
- Não bloquear uma criação por ainda não existir estrutura de relatório.
- Avançar a superfície operacional somente após decisão nova de Rodolfo.
- `SHEIN_US_ES` ainda não existe; criar a pasta apenas quando chegar o primeiro intake espanhol autorizado.
- EN e ES usam a mesma operação e diferem somente pela língua, mantendo copy e assets separados.

Conclusão: o canal continua ativo para conversas naturais de criação sem recriar rotas fixas deletadas.

## Autoridade por canal

O gestor atribuído pode autorizar por pedido, somente no próprio canal e sobre suas contas/perfis:

- criar, duplicar e clonar campanhas;
- pedir relatórios e organizar threads;
- otimizar, pausar e reativar;
- excluir ou arquivar campanhas;
- definir ou alterar budget;
- definir schedule e ativar campanhas.

Budget não exige uma segunda aprovação de Rodolfo dentro desse escopo, mas exige valor e moeda exatos, pre-read do estado atual, menor write possível e GET/readback.

Continuam fora da delegação: billing, `account_spend_limit`, credenciais, ownership, permissões de app, pixel/CAPI estrutural, WordPress, quiz, SMS Funnel, ChatPion, acesso cruzado entre gestores e automação recorrente sem política própria.

Conclusão: solicitante, canal, conta e ação estão dentro da mesma faixa de autoridade.

## Tokens e rate limits

Resolva a arquitetura de credencial sempre no contrato vivo `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json`; não herde o desenho histórico por perfil. A decisão vigente de Rodolfo para `SHEIN-US-DIRECT` usa **Business Integration System User access token** associado ao Business Portfolio cliente, com delegação explícita de ativos; BOT/Messenger continua em User Access Tokens e não faz parte dessa migração. Tokens ficam no 1Password; contrato e registry guardam somente referência do item, alias e metadata segura. Token, App Secret e authorization code nunca entram no Discord, arquivo operacional ou log comum.

Não criar um app por gestor nem tokens adicionais para contornar throttling. Granularidade por finalidade/ativo só é definida depois do inventário e da delegação do Business Portfolio cliente. A Marketing API continua limitada pelo conjunto conta, app, Business Use Case, Access Tier, burst de mutações e frequência por objeto.

No onboarding de cada conta, registrar e monitorar `X-Ad-Account-Usage`, `X-Business-Use-Case-Usage` e, quando aplicável, `X-App-Usage`/`X-FB-Ads-Insights-Throttle`, além dos códigos/subcodes de throttling.

Para a emissão vigente, seguir `paid-acquisition-operations/references/meta-facebook-login-for-business-callback.md`: Authorization Code, `config_id`, `response_type=code`, `override_default_response_type=true`, `state` single-use, troca server-to-server, armazenamento direto no 1Password e readback de `client_business_id`, permissões e ativos. O playbook histórico `references/facebook-login-for-business-onboarding.md` permanece apenas para contexto e não pode sobrescrever o contrato vivo.

Conclusão: a identidade e os ativos são delegados explicitamente pelo Business Portfolio cliente, enquanto quota continua governada pelo conjunto conta + app + BUC + tier + objeto.

## Intake natural de campanha

Os três pedidos-padrão humanos oficiais — criar do zero, clonar com criativos novos e duplicar igual — estão em `references/standard-campaign-requests.md`. Preserve o texto aprovado; verificações internas de conta, compatibilidade site/idioma e evento da fonte continuam no preflight e não devem ser transferidas ao gestor como campos obrigatórios.

Extraia do pedido e do estado live:

```text
Campo                 Regra
--------------------  --------------------------------------------------
gestor/canal          binding exato do contrato
conta/perfil          alvo Meta exato; onboard por readback se novo
site/idioma           yolokfx/vizioid EN ou mavroa ES, conforme contrato
modo                   criar do zero / duplicar igual / clonar com delta
objetivo/evento        fixo SHEIN: OUTCOME_SALES / OFFSITE_CONVERSIONS / ADD_TO_WISHLIST; não pedir ao gestor
estrutura              CBO/ABO, adsets e ads; nunca herdar de CAR
bid                    estratégia e valor quando aplicável
budget/moeda           exatos antes do write
schedule/status        exatos; PAUSED é o fallback seguro
copy                   Primary text, Headline, Description e CTA
criativos              imagens/vídeos reconciliados e language-matched
URL/UTM                destino e parâmetros completos
fonte de clone         campanha/conta exatas quando houver
```

Pergunte somente o campo ausente que bloqueia a ação. Em `SHEIN-US-DIRECT`, o objetivo/evento não é um campo de intake: toda criação, clonagem e duplicação usa `OUTCOME_SALES` com otimização `OFFSITE_CONVERSIONS` e evento `ADD_TO_WISHLIST` (Add to Wishlist). Nos modelos visíveis ao gestor, apresente domínio e idioma juntos em uma única linha no formato exato `Site/idioma: dominio.com - EN|ES`. Pedido vago que mudaria materialmente bid, estrutura, budget, schedule ou destino recebe entendimento curto + pergunta normal; não use formulário obrigatório.

Conclusão: o manifest pode ser materializado sem inventar campos.

## Criação, duplicação e clone

1. Faça GET da conta, campanha fonte e hierarquia dependente quando aplicável.
2. Classifique o modo solicitado; copiar campos para objetos novos não deve ser chamado de clone se a rota não preserva a linhagem da fonte.
3. Feche site, idioma, URL/UTM, copy, criativos, estrutura, bid, budget, status e schedule; materialize sempre `ADD_TO_WISHLIST` e rejeite fonte de clone/duplicação cujo conjunto use outro evento.
4. Reserve criativos e repita a conciliação Drive × Meta imediatamente antes do write.
5. Faça upload sob demanda da mídia nova somente depois que a conta exata do pedido estiver resolvida; para o contrato SHEIN atual, envie apenas a variante vertical em batch paralelo e obtenha IDs Meta prontos. Nunca pre-stagear globalmente nem inferir múltiplas contas.
6. Materialize o manifest e execute validate/plan pelo `meta-campaign-engine-v3`.
7. Execute apenas o pedido autorizado; campanha nova fica PAUSED salvo ativação/schedule explícitos no mesmo pedido.
8. Faça GET/readback consolidado de campanha, adsets, ads, budget, status, schedule, URL/UTM, copy e mídia.

Falha após possível efeito parcial inicia readback-first com o mesmo request/IDs. Nunca repetir POST não idempotente às cegas.

Conclusão: todos os objetos e deltas do pedido têm IDs persistidos e estado live validado.

## Criativos SHEIN

- Original e tratado são uma única linhagem.
- Upload humano começa `RESERVADO_PELO_GESTOR` e `ares_eligible=false`.
- `01_READY` prova prontidão técnica, não ineditismo ou liberação.
- A pasta EN vigente é resolvida no contrato; a existência dela não cria automaticamente um pool ES.
- Nunca usar criativo EN em anúncio ES como se fosse espanhol.
- Antes de selecionar, cruzar Drive IDs, checksums/fingerprint, inventário e IDs Meta/histórico de uso.
- Pastas humanas `USADOS` são evidência de uso, não um novo status canônico nem fonte elegível.
- Drift Drive-only, inventory-only, status divergente ou filename duplicado fica fail-closed até reconciliação.

Ao responder “quantos criativos existem”, separar obrigatoriamente: linhagens tratadas vivas, tratados em `01_READY`, tratados em pastas `USADOS`, originais físicos em `99_LEGACY` e total físico. Original e tratado nunca são somados como dois criativos. Informar horário/fonte do snapshot. Se o operador mostrar uma contagem divergente da interface, refazer inventário API e identificar a pasta/filtro exatos; não atribuir a diferença a paginação ou limite visual quando o contador não estiver visível na evidência.

Conclusão: cada anúncio usa uma linhagem única, compatível com o idioma e comprovadamente elegível.

## Copy e produto

Na linguagem MGS, copy são os campos Meta `Primary text`, `Headline`, `Description` e `CTA`; criativos são somente imagens e vídeos.

O produto/ângulo mostrado no vídeo deve ser identificado por evidência visual da timeline, não apenas pelo filename de upload. Para inventário em lote, amostrar múltiplos frames por vídeo, revisar todo item e ampliar individualmente qualquer ambiguidade antes de consolidar a lista de produtos.

Conclusão: produto visual, idioma e claim não dependem do nome bruto.

## Relatórios e otimização

Todo relatório informa:

- período e timezone da conta;
- moeda;
- fonte Meta e, quando houver ROI, fonte de receita;
- conta/alias e gestor;
- fórmula de ROI/ROAS/custo;
- limitações e divergências.

Não somar contas com moedas ou janelas incomparáveis. Não ativar cron, corte, escala ou otimização automática porque outra operação possui essa regra. Até existir política SHEIN própria, relatórios e ações são on-demand por gestor.

Antes de culpar a campanha por queda, conferir anomalias de entrega, monetização e join de receita quando essas fontes estiverem disponíveis.

Para análises SHEIN de campanha, criativo e produto:

- reconciliar Meta e Smart Bidding por `CAMPAIGN_ID` + conta, comparando `spend` Meta com `INVESTIMENT` antes de calcular ROI;
- filtrar novamente o campo `DATE` retornado pelo Smart Bidding, porque janelas ISO em UTC podem incluir a data civil anterior da conta;
- calcular ROI líquido como `(NET_REVENUE - INVESTIMENT) / INVESTIMENT`; tratar `purchase_roas.omni_purchase` da Meta como sinal complementar, não como substituto da receita líquida;
- não usar `PRODUCT` vazio nem nome de campanha como prova visual final: o rótulo do nome é provisório até revisar a mídia;
- quando `GET /<video_id>?fields=source` retornar HTTP 200 sem `source`, usar `GET /<video_id>/thumbnails`, amostrar quadros distintos do início/meio/fim e manter o produto como não validado se a variedade visual for insuficiente;
- ROI externo existe no nível de campanha/ad set quando o tracking não carrega identidade do anúncio; nesse caso, ranquear criativo por ROAS Meta e gasto, mostrando o ROI apenas como contexto da campanha, nunca como ROI direto do asset.

Conclusão: recomendação ou write usa dados do mesmo período, moeda e chave de junção.

## Discord

- Responder na thread atual.
- Toda thread inclui Zeus e Rodolfo; a lista operation-scoped adiciona Geizian e o gestor do canal.
- Confirmar membros somente por readback real.
- Título: 3–6 palavras, assunto + contexto; não sobrescrever título manual.
- Na fase atual, não criar threads fixas nem threads de relatório/otimização; responder à conversa natural de criação e preservar o histórico.
- As seis threads fixas deletadas por Rodolfo não podem ser recriadas por inferência ou recovery.

Conclusão: resposta, thread e participantes pertencem ao canal/gestor corretos, sem reabrir rotas removidas.

## Pitfalls

1. Herdar `1×1×3`, evento, bid, data ou lifecycle de Creditoparaveiculo só porque ambos são tráfego direto.
2. Tratar autorização de campanha como autorização de billing, credencial ou pixel.
3. Considerar `01_READY` ou uma pasta `USADOS` prova suficiente de elegibilidade.
4. Misturar os três sites sem registrar idioma e URL final por anúncio.
5. Reutilizar conta/perfil de outro gestor para contornar falta de acesso.
6. Criar cron/otimização recorrente a partir de um pedido pontual.
7. Reportar ROI sem fonte de receita, período, moeda e timezone comparáveis.

## Verificação

- [ ] Contrato SHEIN vivo carregado
- [ ] Canal, gestor, conta e perfil reconciliados
- [ ] Site e idioma compatíveis com copy/criativos
- [ ] Objetivo/evento fixos `OUTCOME_SALES` / `OFFSITE_CONVERSIONS` / `ADD_TO_WISHLIST`; estrutura, bid, budget e schedule resolvidos
- [ ] Authority do pedido confirmada sem ampliar escopo
- [ ] Criativos reservados e conciliados Drive × Meta
- [ ] Engine v3 validate/plan concluído para criação/clone/lote
- [ ] Write mínimo e GET/readback completos
- [ ] Período, moeda, timezone e fontes declarados em relatório
- [ ] Zero herança implícita de CAR/CPV ou de outro gestor
