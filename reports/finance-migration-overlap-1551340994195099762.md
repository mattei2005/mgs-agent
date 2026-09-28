# Agosto/2026 — coexistência de Rede1 CAD e AV USD

Autoridade: Rodolfo1551340994195099762, thread1545426987756298340. Fonte: oito abas frescas da planilha1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g, acessadas somente por GET com a Service Account canônica.

## Decisão confirmada

CAD gross da dash deve igualar CAD da planilha; USD gross deve, separadamente, igualar USD da planilha. Wantabrand principal USD4,604.04, confirmado novamente pelo consolidado M2; literal escrito pelo usuário: `4,604,04`.

A migração da AV ocorreu aproximadamente em17/08, não em um corte universal obrigatório. Receitas da Rede1/CAD e AV/USD podem coexistir no mesmo domínio/dia. No detalhamento, manter duas entradas de receita com a mesma data e fontes/moedas próprias; no consolidado diário somar CAD/USDCAD+USD. Não substituir uma receita pela outra, duplicar gasto de mídia nem somar novamente um legado já combinado. A janela15–25 é de conferência, não limita a completude do fechamento mensal.

## Evidência da conferência solicitada

A auditoria de15–25/08 encontrou13domínios/subdomínios e20pares domínio/dia com ambas as receitas não-zero. Linhagem de4.538linhas da janela preservada. Somente nesses dias simultâneos: CAD19329.63469516996041622794 na Rede1 e USD2739.78 na AV. Os valores não são somados entre moedas nem representam o total mensal.

Dias simultâneos por domínio:
- de.newsoun.com:17/08.
- eggbev.com:18,19,20/08.
- finance.topfeed.fun:19/08.
- finanzas.eggbev.com:18/08.
- finanzas.newsoun.com:17/08.
- finanzas.openzed.com:18,20/08.
- finanzas.topfeed.fun:19/08.
- finanzas.zuout.com:21/08.
- finanzas.zytiva.com:17/08.
- lyzmo.com:17,20/08.
- newsoun.com:17/08.
- openzed.com:18,19,20/08.
- zytiva.com:17,18/08.

Eggbev, valores originais:
-18/08: CAD356.6280056428271922 + AV USD1479.31.
-19/08: CAD5309.3455776611589972 + AV USD0.16.
-20/08: CAD7971.92636996096082944 + AV USD0.01.

Controle de subcentavos: de.newsoun.com tem CAD0.004317552897398294 e AV USD13.91 em17/08. A receita CAD participa da soma mesmo exibindo0,00.

Datas ambíguas por locale nas três adições históricas de relatórios afetam apenas dias1–12 e não podem pertencer à janela15–25 sob nenhuma das duas leituras;1.114registros foram explicitamente classificados fora da janela, não apagados, zerados nem redistribuídos. As724datas string US foram interpretadas explicitamente. Valores brutos permanecem preservados.

## Mapeamentos aprovados, não generalizar

Somente para o fechamento de agosto e os domínios exatos:
- eggbev.com + b01fb01c13 → br-car-br.11linhas, USD173.04, medium g006-s (Nicolas/direto).
- zytiva.com + pg_22100 → gb-cc-en.256linhas, USD7381.14, medium g003-d (Isliago/BOT).

As confirmações são prioritárias para esses códigos exatos, preservando o tracking bruto. Não estender aos códigos vizinhos, outros domínios ou outros meses; a proposta de aplicar maior vertical indiscriminadamente continua NÃO aprovada. Os valores acima já fazem parte da AV, não são receita adicional.

## Estado e continuidade

Conferência e registro das duas decisões concluídos; nenhuma escrita financeira ou na planilha neste turno. A correção geral de gross e a representação das duas fontes no detalhamento da dash ainda NÃO foram aplicadas. Os pontos1e3 aplicados na etapa anterior permanecem uma entrega distinta.

Evidências: apps/finance-system/private/migration-overlap-1551340994195099762/{summary.json,overlap-by-domain.json,overlap-by-day.json,window-source-lineage.json,confirmed-mapping-rows.json,audit_overlap.py}. Procedimento atualizado na skill mgs-finance-dashboard, references/adops-monthly-source-reconciliation.md.

Próximo passo: fechar os demais mapeamentos ainda não comprovados, implementar a coexistência por fonte/moeda sem repetir mídia e aplicar o mês completo com recuperação/transação/readback. Não confundir esta conferência com fechamento financeiro já concluído.
