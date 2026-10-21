# Setembro 2026 — ponto 1 / SB Rede1 concluído

## Autoridade e escopo

- Rodolfo1562583090235318283 confirmou o relatório AdOps de setembro como valor correto da receita, atribuiu as reduções a dedução de receita do GAM e autorizou ajustar todos os domínios do ponto1, conferir100% e somente depois seguir ao ponto2.
- Fonte canônica deste ajuste: spreadsheet`1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA`, aba`rede 1 SB`, gid565588781, competência2026-09. A planilha geral não participa e a planilha de conferência é somente leitura.
- Rodolfo1562583923022766212 acrescentou uma observação em Pagamentos deG003/Isliago, explicando a redução de Zytiva por dedução GAM.
- Este fechamento supersede os estados de explicação/aguardando aplicação somente do ponto1. Rede2, Facebook, Google, M2, AV, pagamentos e demais pontos não foram ajustados. Agosto e outras competências preservados.

## Resultado financeiro verificado em produção

- Receita SB Rede1 antes: CAD783034.41730848215352174241.
- Relatório: CAD778884.56398680319913306997.
- Dash após: CAD778884.56398680320482561909.
- Ambos exibem **CAD778.884,56**; diferença monetária em centavos **CAD0,00**.
- Redução global: **CAD4.149,85**, calculada antes de arredondar.
-98 campos de receita corrigidos em11 sites: Eggbev,FinanceAdx,FinanceTopFeed,Helixenit,Infinitynexx,Lyzmo,Newsoun,Openzed,Openzed Finanzas,Yolokfx,Zytiva.
-3050 linhas originais preservadas;1186/1186 controles de domínio/país/dia coincidem em centavos, cobrindo38 sites. Nenhum controle faltante e nenhuma receitaCAD adicional fora do conjunto.
- Precisão: resíduo agregado entre representações decimais =5.69254912E-12CAD; preservado na evidência, sem lançamento compensatório. A afirmação100% refere-se à paridade monetária em centavos, não igualdade textual de números decimais de representações distintas.
- Zytiva: CAD37610.27618273529476620297, exibidoCAD37.610,28; reduçãoCAD3.580,73.
- Aplicação atômica em workspace-2026-09: revisão1646→1647, audit4937/SEPTEMBER_REDE1_GROSS_RECONCILED. Última leitura1648 contém somente atualização posterior de FX automático4938;98 correções permanecem idênticas.

## Representação e preservação

Usado o overlay nativo`gross_pair` em98 entradas já existentes, sem alterar os imports originais. Cada overlay mantém a autoridade, arquivo/gid, linhas de origem, SHA-256 da fonte, CAD anterior e método. ReceitaUSD preservada; IDs, gestor, estratégia, país, data e vertical existentes preservados.

Regra aprovada de Yolokfx01–09 mantida: em três dias com dedução real, recalculado somente o complementoG002 a partir do novo total, preservando as parcelas dos gestores que haviam sido aprovadas por SB. Diferenças de atribuição com total igual não foram misturadas ao ponto1 nem transferidas entre gestores por inferência.

O motor recalculou receita líquida, imposto, lucro e remuneração. Cinco visões de gestor passaram a reconciliação após o ajuste. Checagem final read-only implantada:15/15 combinações de competências×gestores aprovadas, zero falhas. Taxas/regras/câmbios fixados, mídia, Despesas Gerais, SMS e ledger preservados; nenhuma transferência, quitação ou novo desconto financeiro.

## Backup, ensaio e transação

- Dump completo remoto privado:`/home/zeus/mgs-finance-backups/rede1-close-1562583090235318283/finance-before.dump`.
- Cópia local ignorada pelo Git antes da captura:`apps/finance-system/private/september-closing-1562564679400951829/rede1-before.dump`.
- SHA25669cdcf64454c07fd1b09fed2a87915b0d4efb6c4ab36f0c2228f94dfa5835634;143007985bytes; catálogos validados e cópia reversa com hash idêntico.
- Restauração materializada:`mgs_finance_rede1_1562583090235318283`;235 cenários no backup com fingerprints equivalentes. Banco de ensaio retido; não houve exclusão.
- Stage remoto:`/home/mgsfinance/stage-rede1-1562583090235318283`;65 arquivos fonte e fixtures explícitas, Node copiado com hash idêntico para respeitar os diretórios privados; papel peer administrativo usado somente no banco isolado.
- Ensaio de cálculo, aplicação isolada, readback e idempotência validados antes de produção. Transação produtiva usa rolemgsfinance, lock de linha, guard de revisão, recuperação imutável e audit.
- Recovery produtivo:`recovery-rede1-1562583090235318283`, contendo o estado exato anterior ao commit. Provas durante a transação: outros cenários e ledger inalterados.
- Entraves do ensaio recuperados: restrição peer do banco de teste, fixture opcionaldomain.json inexistente remotamente, executável Node sob diretório privado, campoerror omitido quando zero e identidade do recovery no validador. Foram corrigidos apenas o ambiente/validador de teste; nenhuma permissão/configuração de produção ou assertiva monetária foi relaxada.

## Observação em Pagamentos — G003/Isliago

- Publicada em setembro/2026, beneficiário`personnel|151`.
- Note ID`zytiva-september-close-1562583923022766212`; audit4940/PAYMENT_NOTE_ADDED.
- Texto explicaCAD41.191,00→CAD37.610,28, reduçãoCAD3.580,73, deduçãoGAM confirmada pela gestão, dias/operações corrigidos e atribuiçãoG003 preservada.
- Explica expressamente que a redução é de receita brutaCAD, não um desconto do mesmo valor na remuneração; não cria outro ajuste nem pagamento no extrato.
- Observação é metadata append-only no audit, lida após a autorização existente de beneficiário/gestor. Não foi criada linha financeira fictícia, zerada ou anexada ao ajusteSMS anterior.
- Código publicado pelo controlador canônico, release`payment-note-1562583923022766212`: finance-ops.mjs,public/operations.js e teste existente ampliado. Nenhuma mudança de credencial/permissão/schema. Somente serviço financeiro recarregado; não houve alteração de PostgreSQL/gateway.
- Gates integrais:279 testesNode e231Python, todosPASS, sem skips. O gatePython foi reexecutado de forma silenciosa após limite de transporte; resultado final consumido.
- Stage real isolado:10 checks, owner/partner/gestor, desktop/mobile, reload, escape de texto, privacidade entre gestores e competências, saldos/ledger invariantes.
- Readback público autenticado com MFA do Owner e prévia legítima de Isliago:12 checks, desktop/mobile, nota visível apósreload, conteúdoAPI exato, outros gestores sem acesso, agosto sem nota, zero errosJS e zero POST financeiro. Sessão de validação encerrada ao final.
- Antes/depois da publicação do código:236 cenários e33 registros do ledger com fingerprints idênticos. Inclusão da nota também preservou cenários/ledger/saldos integralmente.

## Evidências e continuidade

- Financeiro:`apps/finance-system/private/september-closing-1562564679400951829/` — point1-apply-plan.json, point1-backup-receipt.json, point1-stage-*.json, point1-production-apply.json, point1-production-verify.json, point1-final-independent-checks.json, completed-snapshot.json e readbacks de fonte.
- Observação:`apps/finance-system/private/payment-note-1562583923022766212/` — note.json,note-recorded.json,stage.json,manifest.json,live-browser.json,gate attestations e fingerprints.
- Fontes relidas após os ajustes; nenhuma alteração de valores/fórmulas na planilha.
- Procedimento reutilizável atualizado em`mgs-finance-dashboard/references/adops-monthly-source-reconciliation.md` e relido.
- Checkpoint principal:`ZEUS-FINANCE-SEPT-CLOSE-1562562282838429729`.
- Próxima etapa: **ponto2/SB Rede2**, ainda intacto. O saldo bruto a conferir permaneceUSD31,73 (CreditoparaveiculoUSD30,24;GameZoneAdUSD1,49). Não iniciar outra correção antes da sequência definida com Rodolfo.
