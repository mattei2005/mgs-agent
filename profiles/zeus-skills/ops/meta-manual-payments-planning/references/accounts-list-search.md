# Accounts list — teste de busca por saldo

## Autoridade e resultado

Rodolfo autorizou testar cerca de cinco contas na mensagem `1564379257491296286`, thread `1563926766286803004`, usando Billing & payments > Accounts > Ad accounts e busca por nome. Teste somente leitura concluído em cinco contas, com pixels e AX reconciliados, em uma única aba própria e zero páginas de detalhes abertas. Evidência: `reports/meta-billing-accounts-search-1564379257491296286/collection.json` e `verified-results.json`. O teste inicial não autorizava rollout. **Autorização posterior `1564382301155098717` (“pode terminar o resto então”) aprovou concluir o mesmo workbook/38H pela busca Accounts validada.** Nesta recuperação, H recebe o Current balance da linha exata, com fonte `accounts_list_current_balance`, sem fingir leitura do modal ou prova de botão desabilitado. Preservar47IDs,moeda,notas/horários e demais colunas. A autorização não altera billing/cadência nem permite confundir a medida com limite do cartão.

## Procedimento validado

1. Descobrir a janela Chrome aprovada novamente, obter a lease PC1 e abrir uma aba própria. Acessar `/adsmanager/billing_hub/accounts` com `business_id=155263197283282` e os parâmetros aprovados pelo usuário. A lista permanece na mesma URL ao trocar a busca; `asset_id` e `payment_account_id` da URL são contexto fixo, **não** o ID de cada resultado.
2. A busca visual tem placeholder `Search by name…`, mas o AX exercitado a expõe como **role Edit, label Search**. Exigir um Edit/SearchBox único e captura fresca; um Text/Search não é campo editável. Não exigir o texto literal do placeholder nem o cabeçalho Current balance no AX: este pode omitir o header mesmo com linhas completas.
3. Focar a busca e substituir seu conteúdo pelo nome exato. Aguardar resultado contendo nome, `ID:` e saldo monetário na mesma linha; verificar pixels, cabeçalho Current balance, nome completo e ID da linha. Não abrir o hyperlink da conta nem clicar Pay now.
4. Busca é por substring/prefixo e pode devolver várias contas. Exemplo comprovado: Infinitynexx-MX-CC-ES-01 retornou também Infinitynexx-MX-CC-ES-01-G001, com outro ID, outro saldo e outro funding. Selecionar pelo ID exato e nome completo, nunca primeiro resultado nem valor mais próximo.
5. Manter saldo, método e status associados à mesma linha. Persistir cada leitura com hora original e screenshot. Dólar na UI sozinho não define moeda; resolver pela fonte Meta/contrato USD aprovada.
6. Fechar somente a aba própria e liberar lease. Login/2FA ou bloqueio temporário explícito interrompem o teste, sem contorno por perfil ou abuso de reload. Uma Accounts list carregada com sucesso não prova liberação da rota de detalhes ou modais.

## Limite semântico

A coluna da lista é **Current balance**. Sua leitura bem-sucedida prova o saldo exibido, não o valor permitido no modal Pay now, o status de invoice, pagamento efetuado nem a indisponibilidade financeira do botão. A publicação H da recuperação foi autorizada explicitamente em `1564382301155098717`; usar o saldo literal da lista com a nova fonte declarada e sem atribuir o rótulo Amount you can pay now. Fora desse escopo, preservar o gate vigente ou obter aprovação explícita; o teste isolado não seria autorização. I/current balance pode usar essa evidência sob pedido de publicação, sem inventar uma equivalência com o modal.

O teste de cinco contas não alterou Sheets, Meta billing, cron nem a regra já agendada. Não copiar valores históricos desta referência como se fossem atuais.
