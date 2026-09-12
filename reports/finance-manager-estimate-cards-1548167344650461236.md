# Três cards de estimativa nas abas dos gestores

## Autoridade e escopo

- Pedido direto de Rodolfo: `1548167344650461236`.
- Thread: `1545426987756298340`.
- Escopo: acrescentar uma segunda linha com três cards de estimativa em todas as abas de gestores, imediatamente abaixo dos três cards existentes.
- Sem alteração de valores financeiros, regras de remuneração, permissões, credenciais, banco, planilhas ou gateway.

## Implementação

A nova linha reproduz as três métricas úteis da linha `ESTIMATIVA / MÊS` das planilhas dos gestores, já expostas pela API como resumo `row=14`:

1. `Resultado líquido estimado` ← `row14.profit`.
2. `Referência 7% estimada` ← `row14.commission7`.
3. `Referência 10% estimada` ← `row14.commission10`.

Cada card mostra:

- USD como valor principal;
- BRL em tamanho menor, convertido pela cotação do mesmo mês;
- `—`/conversão indisponível quando a fonte ou a cotação não existir, sem inventar zero.

Os três cards existentes foram preservados. As referências de 7% e 10% continuam apenas informativas; a remuneração efetiva não foi recalculada nem alterada por este pacote.

## Arquivos

- `apps/finance-system/public/operations.js`
- `apps/finance-system/tests/manager-layout.test.mjs`
- `apps/finance-system/private/manager-tabs-audit-1548145007612137554/browser.mjs`
- `apps/finance-system/private/manager-estimate-cards-1548167344650461236/release.py`

## Testes e readback

- Teste RED confirmou ausência da função/linha antes da implementação.
- Testes focais: `10/10`.
- Suíte Node integral: `129/129`.
- Stage browser: Joe, Isliago, Kelly, Ícaro e Nicolas, três cards por gestor, USD e BRL conferidos contra `row14`, 390px/1440px sem overflow e zero erro JavaScript.
- Produção browser: mesmos cinco gestores e mesmas conferências.
- APIs de produção: `85/85` combinações de 17 competências × 5 gestores preservadas.
- Controle de reconciliação das abas: PASS.
- PostgreSQL: fingerprint idêntico antes/depois.
- Serviços `mgs-finance-dash.service` e `.socket`: ativos; não foram reiniciados.
- Hermes gateway: não reiniciado.
- Hash publicado de `public/operations.js`: `b3176354cff618303b9989926abfed5d44d850197740a447d00e573d074ae9da`.
- Backup/rollback: `/home/zeus/mgs-finance-backups/1548167344650461236/public/operations.js`.

## Falhas tratadas antes do sucesso

1. O primeiro preflight tentou ler um arquivo de produção com o usuário SSH, mas o arquivo é corretamente restrito a `mgsfinance`; não houve escrita. O readback foi corrigido para executar como `mgsfinance`.
2. A primeira tentativa de publicação colocou o novo arquivo, mas o health check usava `curl -f` numa rota autenticada. O `401` esperado foi tratado como erro; o rollback restaurou e validou o hash anterior automaticamente. O check foi corrigido para exigir explicitamente `401`, e a segunda publicação passou integralmente.

Nenhuma dessas falhas deixou alteração parcial em produção.
