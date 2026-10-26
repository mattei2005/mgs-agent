# Funding e prioridades — regra vigente

Autorização: Rodolfo Mattei, mensagem `1564115318887161857`, thread `1563926766286803004`. Esta referência supersede os gates antigos de reorganização e contagens/posições fixas em recurring-refresh.md, pay-now-column.md e september-invoices.md. Schema permanece A:J.

## Cada varredura

1. Priorizar G Média diária, H Pay now, I Saldo a pagar e J Outubro/2026. Uma pendência de prova histórica em D não deve bloquear métricas independentes verificadas.
2. Executar `regroup_funding.py --apply` antes do preflight geral. Lê funding live dos mesmos 47 IDs e move defaults tipo1 de linha para cartão, no bloco superior da MESMA aba. Não muda billing na Meta. Preserva notas, links, dados e ordem relativa; reconstrói títulos/subtotais com backup e readback integral. Transição inversa/unknown bloqueia explicitamente sem perder contas. Invoice antiga continua vinculada à conta mesmo depois da troca de default: preservar E/F e incluir F no subtotal de cartão quando houver invoice; o funding atual nunca apaga uma dívida histórica.
3. A quantidade de linhas é dinâmica e guardada no contrato por IDs. Não fixar 39/38 nem header na linha13. `publish_pay_now.py --prepare` exige igualdade com `pay_now_account_ids`, não contagem histórica.
4. Executar `refresh_workbook.py --apply --allow-history-pending`: publica só C/G/I/J e preserva D, retornando status qualificado e contas pendentes quando necessário. Completar D somente com prova do instrumento da transação; ausência de prova é pendência UI, não assertion genérica. Não usar evento genérico/default para preencher D.
5. Coletar e inspecionar todos os modais dos targets atuais, publicar H com hora individual real, sem pagar. Uma recuperação da publicação usa o mesmo timestamp da coleta, nunca finge nova leitura.
6. Ler invoices live e publicar E/F. Rodolfo informou que setembro foi pago na quinta-feira e esperava baixa no dia seguinte à mensagem. Isso é pagamento informado pelo dono/baixa Meta pendente, não status Paid confirmado. Não zerar F antes da baixa live nem repetir pagamento.
7. Reconciliar Insights diário/agregado por conta. Se diferirem, fazer no máximo duas novas leituras limitadas à mesma conta/período, registrar os totais anteriores/posteriores sem URLs tokenizadas e manter a tolerância monetária existente. Se persistir, preservar o snapshot anterior e reportar a conta, campo e diferença; não atribuir automaticamente a arredondamento ou virada de dia sem prova.
8. Validar 47 IDs, agrupamento, G/I/J de todas as contas, H de todas as linhas atuais, fórmulas/links e preservação das outras abas. Cobertura parcial de D fica explícita. Manter cadência anterior, sem criar writer paralelo.

## Identificação e pixels

- Filename e URL solicitada não provam identidade final. Ler pixels e AX da conta/BM reais.
- Não normalizar OCR de ID divergente. Preservar original e usar crop nativo da URL; em 1456x791, [200,25,1100,65] mostrou o asset_id. Crop só à direita pode conter session_id/payment_account_id e produzir falsa leitura. Não confundir esses parâmetros.
- Se `pending_card_history.status=blocked_capture_parity` no contrato, não consumir outra tentativa idêntica. Primeiro provar que a captura nova contém os mesmos conta/BM e histórico no AX e nos pixels, sem tocar abas pessoais; sem essa prova, manter apenas D pendente e continuar os campos independentes autorizados.
- Captura de outra página não é logout da Meta. Se AX e screenshot divergirem, não marcar transação como visualmente confirmada nem interagir com a outra página. Preservar evidência e qualificar a lacuna. Screenshots anteriores corretos não validam a captura divergente.
- Em aba própria, focar barra antes de digitar e aguardar render. Preservar screenshot diagnóstico antes de fechar somente a aba criada. Não tocar abas pessoais preexistentes. Depois de repetidas divergências, parar a rota e manter checkpoint; não insistir em autenticação inexistente nem alterar runtime global para completar D.

Primeira reclassificação validada: Mavroa-US-SHEIN-ES-03-G003, ID1543098427832443, foi para cartão; 47 IDs preservados, 9 cartão/38 linha, nenhum write Meta. Evidência histórica em reports/meta-manual-payments-runs/regroup-20261025T231838109427. Contagens e valores devem ser revalidados em cada tick.
