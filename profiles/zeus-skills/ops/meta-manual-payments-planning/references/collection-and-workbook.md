# Coleta Meta e workbook de planejamento

## Identidade e parâmetros

- Resolver a credencial Meta BM-admin existente no 1Password pela operação aprovada e validar `/me`, permissões e a BM exata; não copiar tokens para esta skill ou argumentos de shell. Os itens podem mudar: nomes/IDs de credencial não são fixados como verdade nesta referência.
- Graph `v26.0` foi a versão efetivamente exercitada no caso inicial. Validar versão suportada ao retomar; não extrapolar campos/tipos sem readback.
- Meta é leitura: GETs diretos ou Graph batch transport POST com filhos exclusivamente `method=GET`. Transport POST não autoriza pagamento ou mutação Meta e não contorna quota.
- Para diagnóstico Google do alvo, usar `terminal(command="python3 /root/mgs-agent/scripts/mgs_google_workspace_auth.py --check-drive-id <SPREADSHEET_ID> --check-sheet-id <SPREADSHEET_ID>", timeout=180)`. Esse comando não publica tokens. O consumer real deve importar o mesmo helper, validar `project_id` e `client_email`, e usar `api_json` com quota project `mgs-core-prod`.

## Inventário e funding atual

Paginar `/{business_id}/owned_ad_accounts` e `/{business_id}/client_ad_accounts`; não usar apenas `/me/adaccounts` nem inventário de token operacional como total BM. Deduplicar por `account_id` e manter contagens de cada origem.

Projeção de conta exercitada:

`account_id,name,account_status,currency,timezone_name,business,funding_source_details,balance,is_prepay_account,user_tasks`

- `funding_source_details.type=1`: cartão atual; publicar somente display string validada com bandeira/final mascarado. Tipo 1 sem sufixo é cartão não identificado, não uma conta a descartar.
- Tipo 4 com display `monthly invoicing`: linha de crédito atual. Cartão default nessa linha é não aplicável; um cartão disponível para pagamento avulso não vira automaticamente default.
- Ausência de funding após exact-account GET é lacuna; não deduzir por nome/status/gasto.
- Para o fluxo PC1, seguir a seção **Inventário de cartões no PC1 — mapear antes de abrir** do SKILL.md; ela concentra a ordem obrigatória, exclusões, estados de cobertura e formato de entrega. Os campos API acima descrevem funding atual, não o conjunto de cartões adicionais cadastrados.
- Na UI PC1, o detalhe de cartão e o de monthly invoicing têm marcadores de prontidão diferentes: aceitar a seção de métodos junto ao rodapé suportado correspondente (`How ads billing works` ou `About monthly invoicing`), não exigir Currency em todas as contas. Lista Accounts pode manter linhas anteriores offscreen no AX e truncar a cauda: estabilidade da contagem não prova fim; conferir posição final em pixels, ausência de continuação e cobertura dos IDs.
- Classificar `temporarily blocked`/`going too fast` pela superfície exata: **Accounts acessível não comprova liberação dos detalhes de billing**, e algumas leituras bem-sucedidas não comprovam recuperação integral. Na tentativa adiada autorizada, fazer uma única navegação de teste ao primeiro ID pendente; se passar, retomar somente os faltantes e interromper ao primeiro novo bloqueio. Se não passar, preservar o ledger e reportar a dependência real, sem reabrir contas, trocar de perfil ou repetir a tentativa imediatamente. O intervalo pedido pelo usuário define o horário da nova tentativa, não um prazo de liberação prometido pela Meta.
- `balance` usa unidades mínimas; converter com Decimal segundo moeda. USD/BRL têm duas casas no escopo exercitado. Não generalizar divisor 100 a uma nova moeda sem verificar o expoente.
- Guardar IDs de funding só quando indispensáveis a reconciliação interna da linha; não expor IDs de fontes de pagamento/transações na planilha/Discord.
- No Graph v26, não usar root `ids` para várias contas: essa rota retornou depreciação; usar GET por ID ou batch GET-only.

## Insights mensal e média diária

Rota: `/act_{account_id}/insights`, `level=account`, campos `account_id,account_currency,spend,date_start,date_stop`, `time_range` explícito e `limit` limitado. Ler uma vez com `time_increment=1` e outra com `time_increment=all_days`; esgotar paginação.

- `spend` já está na unidade principal da moeda.
- Exigir ID/moeda corretos, datas dentro da janela e soma diária versus agregado dentro de uma unidade mínima.
- Mês inclui dia atual apenas como parcial, no fuso Meta da conta.
- Média: obter data local via timezone Meta, janela de hoje−3 até hoje−1, soma/3. Datas sem linha de Insights contam como zero, não reduzem denominador.
- Publicar média em centavos e validar soma das médias exibidas nos subtotais. Não confundir isso com projeção de pagamentos ou limite livre.
- Para alias IANA válido ausente do Python, resolver Link em `/usr/share/zoneinfo/tzdata.zi`, preservar a string Meta original e não mudar TZ do host.

## Histórico de cobrança versus instrumento

Rota exercitada: `/act_{account_id}/activities`, `business_id` exato, `category=BUDGET`, janela `since`/`until` e campos `event_time,date_time_in_timezone,event_type,translated_event_type,extra_data`.

- `extra_data` pode ser JSON string. `type=payment_amount` e `new_value` numérico fornecem o valor em unidades mínimas, mas não o instrumento.
- No caso inicial, `ad_account_billing_charge`, `payment_amount` e `action=67` foram **idênticos para Advertising credit e cartão**. Portanto esse triplo não é filtro de cartão.
- Na revalidação API de `1563948130024693871`, a projeção completa do AdActivity (inclusive actor/application/object/tool) e as fontes suportadas `CALYPSO`, `TAO` e `TAO_AD_ACCOUNT` mantiveram a mesma representação de crédito e cartão na conta-controle Eggbev: actor Meta, object ACCOUNT, tool Other e nenhum campo de instrumento. As oito contas foram repaginadas; 92 eventos de cobrança não expuseram instrumento. Não repetir essas variantes como se fossem filtros de cartão. A rota histórica `/transactions` respondeu `100: Tried accessing nonexisting field (transactions)` no v26.0; isso é incompatibilidade de rota, não token inválido nem prova de impossibilidade global da API. Evidência histórica: `/root/mgs-agent/reports/meta-card-api-retry-1563948130024693871.json`; revalidar antes de generalizar a outras versões/rotas/contas.
- Manter internamente timestamp e vínculo de conta; proteger `transaction_id`. Nunca derivar cartão a partir do ID ou de um limiar de valor.
- Procurar evidência suportada de instrumento no registro da transação; se os campos consultados não a trouxerem, declarar a limitação daquele endpoint, não de toda a API. Não inventar rota/field privado como se fosse público.
- UI aprovada/screenshot: exigir método visível, status pago, valor/data e vínculo inequívoco à conta. Screenshot recortado sem nome pode ser associado somente por contexto humano explícito e reconciliação única com a sequência e a célula exata, documentando essa limitação.
- Se uma janela longa falhar, usar intervalos diários semiabertos no timezone da conta, esgotar cada um e deduplicar internamente; preservar checkpoint e respeitar quotas. Não repetir broad cursor indefinidamente.
- UI PC1: carregar `secure-remote-windows-automation` e seu fluxo de navegador real, adquirir lease compartilhada, descobrir janela/perfil e conta antes da consulta, preservar abas preexistentes e liberar lease em finally. Descobrir runtime/interpreter atuais; não copiar o runtime path de um helper histórico. Sem credenciais/cookies exportados, sem alterações de browser/security.

## Invoices e Pay now

Rota `/{business_id}/business_invoices`, paginação completa e projeção explícita:

`id,invoice_id,ad_account_ids,currency,amount,amount_due,payment_status,invoice_date,billing_period,due_date`

- Projeção default pode trazer apenas `id`: não concluir ausência de invoice porque o join por conta ficou vazio nesse retorno.
- Unir por IDs exatos contidos em `ad_account_ids`, não nome ou diferença de valores.
- No retorno exercitado `amount` veio em unidades mínimas; usar também `amount_due.amount_in_hundredths` e a moeda do objeto. Guardar total original e pendência como medidas distintas.
- Número de invoice, competência e status são exibíveis; não publicar invoice download URLs protegidas.
- Modal Pay now: ler rótulo e período da UI/imagem. Valor permitido para pagar agora não é, sem prova, invoice de mês anterior nem total devido; cartão selecionado no modal não comprova uma cobrança passada.
- Para conciliar saldo corrente do mês, ler balance + Insights diário/agregado por GET batch coerente, e juntar os pagamentos confirmados da mesma conta/janela. Se houver igualdade, qualificá-la como observação daquele snapshot. Diferença não prova taxa, atraso, outra invoice ou limite.

## Layout, mutação e validação Sheets

- Resolver `spreadsheetId`, `sheetId`, header, schema e ID de conta nas notas antes de qualquer write; os índices mudam quando colunas/linhas são inseridas.
- Modelo atual por `1564022485366734969`: A conta/B forma/C default/D última cobrança no cartão/E Invoice/F Setembro (saldo de invoice aberto)/G média3 dias/H Pay now/I current balance/J outubro. Esta regra supersede o schema anterior de sete/oito colunas; execução em `references/september-invoices.md`. D e Pay now exigem suas provas próprias, não se inferem de Invoice/Setembro.
- Grupo cartão e grupo linha separados, com faixas de contas e subtotais inequívocos. Se surgirem funding desconhecidos no novo escopo, manter bloco explícito; não enquadrar à força em cartão/linha.
- Manter `RAW` para textos e números; usar `updateCells.userEnteredValue.formulaValue` ou modo USER_ENTERED apenas para fórmulas intencionais. Totais monetários: `ROUND(SUM(...),2)`.
- Nome exato da conta permanece texto; billing link em `userEnteredFormat.textFormat.link.uri`, ID e fuso em `note`. Rota efetivamente mostrada pelo usuário: `https://adsmanager.facebook.com/adsmanager/billing_hub/accounts/details/?business_id=<BM_ID>&asset_id=<ACCOUNT_ID>`. Não substituir por `/adsmanager/manage/accounts?act=...` (Summary). O ambiente pode validar também a variante `business.facebook.com/latest/billing_hub/accounts/details/`; não acrescentar parâmetros opacos não provados.
- Snapshot imutável de valores, fórmulas, notas, link/format e estrutura antes de mudar. Para excluir linhas zero, selecionar somente zeros numéricos do campo mensal autorizado, reunir intervalos contíguos e deletar em ordem inversa após congelar IDs. Não excluir contas Meta.
- Uma resposta ambígua de insert/delete exige readback estrutural antes de retry. Se valores já chegaram e só validação/format falhou, não reaplicar os dados.
- Readback obrigatório: conjunto de IDs de todas as contas, valores/fórmulas completas, cálculo independente de subtotais/total, todos os links para conta/BM certos, moedas, notas de instrumento, cores efetivas de pendência e outras abas preservadas.
- Cores Google podem vir float32 e em `backgroundColor` mais `backgroundColorStyle` espelhado. Aceitar somente equivalência RGB em precisão demonstrada; não enfraquecer validações de conteúdo nem repetir writes já corretos.
- Toda atualização é snapshot datado até aprovação separada de recorrência; não alegar refresh automático ou pagamento executado.
