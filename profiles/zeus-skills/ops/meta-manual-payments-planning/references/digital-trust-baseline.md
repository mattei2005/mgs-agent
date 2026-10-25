# Baseline histórico Digital Trust — não é estado live

## Estratégia e origem

Rodolfo aprovou uma skill separada para apoiar pagamentos manuais com diversos cartões, reduzindo saldo de contas e dependência da linha de crédito. Fonte: mensagem `1563943171392667679` na thread `1563926766286803004`. Criar a skill não autoriza pagamentos, mudança de default, cadastramento de cartão ou automação financeira.

## Binding do workbook inicial

- Spreadsheet: `1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU`.
- Aba criada: `Contas BM Digital Trust`; `sheetId=271321738`.
- Link: https://docs.google.com/spreadsheets/d/1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU/edit#gid=271321738
- BM: Digital Trust, `155263197283282`.
- Conta de conciliação citada: `Creditoparaveiculo-BR-CAR-BR-04-G003`, ID `2633813727134360`.
- Estrutura final do turno: A Nome da conta / B Forma de pagamento / C Cartão usado como default / D Última cobrança no cartão / E Média diária — últimos 3 dias / F Saldo a pagar / G Total já gasto em outubro.
- Nunca tratar IDs de coluna/letras anteriores como contrato após inserções. Revalidar bindings, headers, linhas e schema live ao retomar.

## Autorizações e transformações históricas

- `1563926766286803004`: criar uma aba na planilha fornecida com todas as contas da BM, payment/default/balance/gasto de outubro.
- `1563928807851823286`: remover linhas com zero no então campo mensal E; foram removidas 304 de 351, restando 47 contas. Não é autorização de exclusão automática futura, nem de exclusão de contas Meta.
- `1563929190414160013`: separar cartão/linha e inserir totais abaixo; o snapshot ficou com 8 contas no cartão e 39 na linha.
- `1563935009868353587`: substituir links Summary por Billing & payments.
- `1563937040809201687`: última cobrança para cartões e investigação do pagamento avulso na CPV04/G003.
- `1563938261875953840`: média diária dos últimos 3 dias antes do saldo; a coleta de 25/10 usou 22–24/10 completos.
- `1563939770722156567`: excluir Advertising credit da última cobrança no cartão e persistir regra.
- `1563942798149951489`: Rodolfo afirmou que o Facebook estava logado no PC1 e questionou o fallback. O teste de uma janela não comprovou logout global nem impossibilidade da API.

## Conciliações comprovadas naquele snapshot

### CPV04/G003

Em 25/10/2026 11:32 Eastern, balance e Insights de uma coleta coerente mostraram:

- Gasto de outubro USD 31397.56.
- Pagamento confirmado em 23/10/2026 11:30 America/Sao_Paulo: USD 8785.26.
- Saldo USD 22612.30; diferença de conciliação zero.
- Gasto acumulado até 22/10: USD 28550.18, coerente com a lembrança de 28 mil.
- Default permaneceu monthly invoicing. Rodolfo informou pagamento no cartão; o evento da API isolado não expôs seu cartão nem alocação a invoice.

A invoice de setembro `26877313` foi lida ao vivo na mesma tarefa: original USD 37088.13, status Paid, pendência zero, vencimento 31/10/2026. Na consulta de 152 invoices BM, as quatro vinculadas a essa conta estavam pagas; não surgiu invoice fechada de outubro.

O print Pay now mostrava USD 7312.05 como `Amount you can pay now`, período 01–25/10, com AMEX •••• 3005 selecionado; atrás havia balance USD 22612.30. A diferença USD 15300.25 não coincidiu com invoice original ou pendente da conta. O motivo de o modal permitir pagar só parte do balance permaneceu **não comprovado**. Não transformar esse valor em regra de limite ou dívida de setembro.

### Última cobrança Eggbev

Conta `Eggbev-US-CC-EN-03 (FAX-US-02)`, ID `1481815942722118`:

- USD 3.54 e USD 0.07 em 24/10 eram **Advertising credit**, conforme print de Rodolfo.
- Última cobrança visível e reconciliada no cartão: USD 2000.00, Mastercard •••• 2311, 22/10, status Paid.
- Esses eventos de crédito e cartão tinham o mesmo tipo genérico `ad_account_billing_charge`, `payment_amount`, `action=67` na API consultada. Nunca reutilizar esse triplo como prova de cartão.
- A correção do cartão veio de **API + print**, não da API sozinha. A imagem recortada não mostrava nome de conta; o vínculo foi reconciliado pela célula única USD 3.54, contexto humano e sequência de eventos/valores/datas.

## Histórico de pendências e resolução posterior

**Supersessão explícita:** as seis lacunas de instrumento listadas abaixo foram resolvidas pela consulta autenticada do PC1 autorizada em `1563960055504838767`, com fonte `reports/meta-pc1-card-methods-1563960055504838767.json`. Sete cobranças foram positivamente identificadas como cartão e publicadas na coluna D; Growpowerhub permaneceu sem cobrança localizada. O motivo do valor parcial do Pay now continua não comprovado. O estado corrente está no ledger `data/meta-manual-payments/pc1-card-ledger.json`, no checkpoint da iniciativa e no readback live, não nesta seção histórica.

Após aplicar o critério cartão-only, havia uma cobrança positivamente verificada (Eggbev), seis células D sem valor por instrumento não comprovado e uma conta sem evento localizado. As seis lacunas eram:

- Creditoparaveiculo-BR-CAR-BR-13-G006 — `1046241194533786`.
- Creditoparaveiculo-BR-CAR-BR-14-G001 — `1150399088163771`.
- Financeadx-CA-CC-EN-01 — `1762774024309795`.
- Financeadx-MX-CC-ES-01 — `648687381127947`.
- Infinitynexx-MX-CC-ES-01-G001 — `1052719314075904`.
- OpenzedFinanzas-ES-CC-ES-02 — `1290644206529750`.

Growpowerhub-US-SHEIN-EN-04-G004 (`1419148446852410`) tinha zero eventos BUDGET retornados no histórico completo, portanto D ficou vazia com nota, não zero numérico.

A criação inicial da skill não havia preenchido essas lacunas; a resolução posterior pelo PC1 está documentada acima. Revalidar tudo live ao retomar; não confundir o baseline histórico com um monitor ou com validação atual de cartões.

## Evidência local preservada

- `reports/meta-digital-trust-sheet-1563926766286803004.json` — publicação original.
- `reports/meta-digital-trust-sheet-zero-1563928807851823286.json` — seleção de zeros/47 retidas.
- `reports/meta-digital-trust-sheet-blocks-1563929190414160013.json` — blocos/totais.
- `reports/meta-digital-trust-sheet-billing-links-1563935009868353587.json` — 47 links.
- `reports/meta-digital-trust-last-charge-average-1563937040809201687.json` — médias e conciliação; sua seleção antiga de última cobrança foi supersedida pela correção seguinte.
- `reports/meta-cpv04-invoice-pay-now-1563939359642624103.json` — invoices e diferença Pay now não explicada.
- `reports/meta-card-only-charge-correction-1563939770722156567.json` — correção cartão-only e lacunas explícitas.

Os caminhos acima são relativos a `/root/mgs-agent`. Screenshots e snapshots de scratch são auxiliares e podem ser podados; os relatórios duráveis preservam a evidência essencial e o baseline não depende de credenciais/cookies ou de recriar arquivos temporários.
