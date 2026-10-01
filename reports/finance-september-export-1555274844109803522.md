# Setembro/2026 — exportação integral da dash para as planilhas

## Autoridade e decisão

Rodolfo1555274844109803522, thread1545426987756298340, autorizou preencher integralmente setembro na principal e Kelly/Isliago/George/Nicolas/Joe, criar/remover blocos e reparar fórmulas, copiar despesas/câmbios e completar Caixa Sintético. A dash é a fonte correta e deve permanecer sem qualquer alteração por esta operação. A conferência geral fica para a semana do dia20, não antecipada por esta exportação.

Esta autorização supersede o estado **somente diagnóstico/aguardando aprovação** do relatório `finance-september-export-preflight-1555267485928788099.md`. Não autoriza sincronização contínua, liquidação dos parceiros, pagamentos ou alterações de competências anteriores.

## Resultado aplicado

Concluído2026-10-01T19:19:53Z, fonte final workspace-2026-09 revisão922, cutoff30/09. Os seis IDs/gids originais foram preservados. Alteradas as seis abas Setembro2026 e a coluna de setembro no Caixa Sintético, com oito linhas complementares claramente identificadas para os sites novos. Não houve edição nas demais competências.

-49sites representados, incluindo inativos com sua participação real no rateio;30dias válidos, sem dia31.
-4237fatos da fonte reconciliados; preservados os componentes nativos e as nove receitas legadasUSD de Fincgriffin, que não podiam ser perdidas numa exportação apenas dos additions.
-892entradas de mídia não zeradas,39contas com gasto, moedasUSD/BRL e conversão reconciliadas integralmente. ReceitasCAD/USD separadas e convertidas sem dupla contagem.
-Todos os blocos/resumos dos cinco gestores incluem suas participações reais por site/país/dia;49painéis principais com cabeçalhos e totais próprios. Total permanenteD12 de cada gestor preservado; sites que excedem dez linhas aparecem no quadro adicional e integram o total.
-Despesas gerais, cobranças novas/arquivadas, salários, pisos, faixas7%/10%, rateio de31cotas e encargos reproduzem a fonte. Kelly criativos permanece rubrica separada da remuneração de gestora.
-Caixa usa a rede efetiva de setembro nas deduções, não os rótulos compartilhados do histórico. Openzed é contado uma única vez; os oito sites novos entram no subtotal por linhas complementares85:92.

## Paridade final na revisão922

-Receita brutaUSD759701.3652854780218424206930 → exibição759.701,37.
-MídiaUSD522271.9084650683782311019560 →522.271,91.
-Despesas geraisUSD21198.77927256196412057683292 →21.198,78.
-PessoalUSD14105.48957496940689374368237 →14.105,49.
-Lucro líquidoUSD89302.75869180643988944391603 →89.302,76.
-50%BRL231036.7682680825778771217588 →231.036,77.
-Remuneração como gestorBRL: Kelly5959,79; Isliago14993,54; George/Ícaro3000,00; Nicolas27062,76; Joe3469,04.

O quadro de recebimentos da principal espelha o único pagamento de setembro já ativo na dash: ID8f51d114-b5db-4707-a0d3-024ef95ba34f, referênciaSetembro, data30/09, BRL12310,19, sinal negativo. O registro anulado foi excluído do espelho. Saldo anterior3775,09 +devido231036,77 −pagamento12310,19 =saldo222501,67. A abertura e o devido usam arredondamento em centavos igual ao ledger, sem constante de ajuste. **Nenhum pagamento foi realizado, criado, estornado ou editado na aplicação.**

## Câmbios e preservação absoluta da aplicação pelo executor

-USD/BRL5.1742358613; USD/CAD1.423635; GBP/USD1.3395, valores da fotografia de fonte922, identificados como **provisórios**, não como liquidação confirmada.
-Cada gestor usa o câmbio de setembro via CaixaK2, não o de agostoJ2. A estimativa de um mês com30dias completos reproduz o realizado, removendo o divisor antigo de seis dias.
-Esta é uma exportação única, não um espelho continuamente sincronizado. Futuras cotações automáticas ou ajustes feitos na dash podem produzir nova diferença até outra atualização autorizada.
-Durante a execução, a automação de câmbio já existente e um refresh do próprio Rodolfo avançaram a fonte918→922. Audit2735,2738,2739 e2741 comprovam AUTO_QUOTES_UPDATED; somenteUSD/BRL eUSD/CAD mudaram nos overrides. Additions e ledger permaneceram iguais. Não foi tratada como anomalia nem houve alteração no cron/configuração para congelá-los.
-Aplicação acessada por SELECT em transações READ ONLY e pela função de leitura de ledger em conexão default_transaction_read_only=on. Zero endpoint de mutação, zero escrita financeira/configuração/credencial/código na dash. Última consulta confirmou revisão922 e ledger íntegro.

## Validações e recuperações

-80.968células planejadas de entrada/fórmula lidas de volta nas sete superfícies: zero divergência.
-76.479resultados numéricos/formulares comparados com a fonte: zero divergência financeira; maior resíduo raw5.478771217588e-10, inferior a qualquer centavo. Verificação adicional de arredondamento encontrou zero diferença em centavos.
-Zero erro de fórmula exibido ao final; cadeia principal→gestor→folha→consolidado relida integralmente.
-Diff completo antes/depois: zero alteração fora das regiões aprovadas.156abas protegidas relidas e hashes iguais; nenhuma outra competência alterada.
-Seis canários de escrita/leitura/restauração passaram, incluindo funções/decimais en_US ept_BR; nenhuma célula sentinela permaneceu.
-IDs/gids,30datas de cada gestor, tiposDATE/BRL, congelamento de cabeçalho e49barras de título relidos pela API. Não foi usado acesso Google alternativo nem navegador pessoal.
-A primeira validação offline não aceitava decimal abreviado `.1`; o parser foi corrigido e76.479cálculos passaram antes da aplicação. No canário de Kelly, o Google normalizou`.1` para`0.1`: as60diferenças eram lexicais, não financeiras. O verificador passou a aceitar apenas essa normalização comprovada; a planilha já aplicada não foi reexecutada.
-Na etapa intermediária da principal,92erros transitórios de importação apareceram antes de concluir as demais planilhas. Após terminar o cluster e aguardar a propagação normal, o readback completo retornou zero erros e todos os resultados corretos. Nenhum salário foi hardcoded para esconder cache. Pendências operacionais finais:0.

## Backup e evidência

Diretório privado: `apps/finance-system/private/september-export-1555274844109803522/`.

-Backups completos dos seis alvos, Caixa e metadados: `*-before.json`, `*-metadata-before.json`, `backup-manifest.json`; hashes dos seis backups revalidados ao final.
-`implementation/`: código executado e comparadores; não instalado como cron nem automação produtiva.
-`plan.json`, payloads e recibos: aplicação inicial918; `final-922/plan.json`, `fx-final-apply.json` e `verification-final.json`: fotografia final922.
-`final-922/scope-proof.json`, `format-proof.json`, `dashboard-preservation-readback.json`, `completion.json`: provas independentes finais.
-Manifesto selado121arquivos: SHA256 `8da7b6edcf940bd9f697c34424be6130a8b4ec2409b57a87522e28495d6bd201` de `sealed-manifest.json`. Backups privados preservados; nenhum descarte feito. Houve verificação de backup, não um restore destrutivo das planilhas produtivas.

Procedimento reutilizável salvo na skill mensal, `references/dashboard-to-sheets-native-export.md`, com regras de fonte nativa+legada, atribuição, câmbio provisório, locale, propagação e readback integral.

Checkpoint: ZEUS-FINANCE-SEPTEMBER-EXPORT-1555267485928788099. Estado final: exportação concluída e validada; a revisão geral prevista para a semana do dia20 não foi executada nem marcada como concluída.
