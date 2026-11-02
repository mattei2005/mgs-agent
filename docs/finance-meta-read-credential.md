# Credencial de leitura Meta da Dash financeira

Dono: Rodolfo / Zeus. Autoridade: confirmação explícita1566815743050260602 na thread1545426987756298340, após pergunta delimitando o vínculo do financeiro. Resposta: testar o item de25/10 e usá-lo se funcionar. O preflight real passou; não é autorização para criar/rotacionar tokens, editar1Password, conceder permissões, fazer billing ou alterar campanhas.

## Referência confirmada

- Item imutável1Password: `4c2p3bon37smfbklfhuej5ywkm`.
- Vault: `ghkdcenuzsp57w37nzhxuxnkj4` / MGS Conteúdo.
- Título informativo observado: `APP NOVO 25/10 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei`. Resolver pelo ID; o título pode mudar.
- Identidade validada: Roosevelt Mattei, user_id `10233237854144701`, token tipo USER, app_id `1299247318762949`.
- BM de descoberta: Digital Trust `155263197283282`. Escopos de leitura necessários `ads_read` e `business_management` comprovados; permissões mais amplas não autorizam usá-las neste consumidor.
- Google Ads mantém sua identidade/MCC e fluxo anteriores; nenhuma mudança Google neste cutover.

## Consumidores e limites

`meta-lookup-worker.py:META_TOKEN_ITEM` é a referência única do leitor financeiro. O inventário e os dois caminhos de `finance_spend_sources` usam essa mesma referência; evitar hardcode de título datado ou fallback implícito para outra identidade. Cache financeiro isolado e protegido: `/root/.cache/mgs/finance-bm-inventory-meta-4c2p3bon37smfbklfhuej5ywkm.json`, gerenciado pelo helper existente; segredo permanece fora do Git e nunca aparece em logs/relatórios. Cache anterior preservado para rastreabilidade; não apagar nem recriar credenciais por inferência.

Esta decisão supersede somente a busca financeira pelo título `APP NOVO 02/09 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei`. Não altera arquitetura de Ares, BISU, contas operacionais ou outros agentes. A variável histórica FINANCE_META_ITEM não deve escolher silenciosamente outra credencial neste caminho fixado.

## Validação e estado

Pré-condição real: `/me`, `/debug_token`, permissões paginadas, BM, conta exata, campanhaGET e Insights01/11, todos em leitura. A coleta completa pelo candidato verificou391contas:351Meta,13Google disponíveis e27Google conhecidamente indisponíveis;43contas com gasto positivo passaram coleta detalhada. Fontes indisponíveis não viraram zero.

Evidência: `apps/finance-system/private/recovery-1566802212548517990/meta-candidate-preflight.json` e `apps/finance-system/private/meta-binding-1566815743050260602/`. Estado de publicação e recuperação final: checkpoint `ZEUS-FINANCE-RECOVERY-1566802212548517990` e `reports/finance-recovery-1566802212548517990.md`; esta decisão não substitui o readback do runtime.

Após qualquer nova troca do item/identidade, voltar ao gate de confirmação/preflight. Não reabrir esta mesma confirmação após título renomeado quando o ID fixado e a identidade continuam comprovadamente iguais. Falha de autenticação/escopo deve permanecer bloqueio explícito, nunca gasto zero.
