# Relatórios genéricos — seleção positiva e fontes financeiras

Use para pedidos como todas as contas, gasto total, cobranças ou faturas. O recorte permanece o cadastro positivo Ares, mesmo que o solicitante não cite uma operação. Não consultar inventário global, sessões de outros agentes ou portfólios descobertos pelo token.

## Executor read-only

`/root/mgs-agent/scripts/ares-scoped-report.py` implementa `plan`, `inventory`, `spend`, `charges` e `invoices`.

- `plan` resolve a seleção exclusivamente em `data/ares/asset-scope.json`, sem credencial/HTTP. Qualquer ID desconhecido ou malformado interrompe a seleção antes de acesso externo; não corrigir tokens recebidos.
- Execução exige período civil explícito e item corporativo vinculado, resolvido pelo contrato da operação/conta. O item é referência, nunca valor de token. Não escolher credencial administrativa, de outro agente ou de maior alcance após uma recusa.
- `inventory` valida a conta e `business.id`, projeta moeda, fuso, saldos/gasto na unidade retornada e somente o tipo da forma de pagamento. Não salva instrumento, final de cartão, funding source ID ou payload bruto.
- `spend` usa Insights account-level e preserva a moeda/data da fonte. Somar moedas separadamente e normalizar somente campos de unidade comprovada; `amount_spent` de configuração não substitui gasto da janela.
- `charges` pagina atividades da própria conta na janela explícita, seleciona eventos de billing e projeta apenas tipo, horário e campos monetários reconhecidos. Valor sem unidade comprovada permanece como retornado, não convertido por inferência. Não atribuir o cartão atual a uma cobrança antiga.
- `invoices` consulta exclusivamente o edge `business_invoices` da BM operacional, em GET, com `ad_account_ids` obrigatório no retorno. Qualquer fatura sem contas comprovadas no cadastro é retida. Não consultar outra BM, seguir URLs de PDF ou buscar fatura por ID desconhecido. Período usa `issue_start_date` inclusivo e `issue_end_date` exclusivo conforme documentação Meta.

O executor usa Graph Batch com filhos GET e paginação por cursor no mesmo path aprovado; nunca segue `paging.next` como uma URL autenticada arbitrária. Progresso concluído é preservado antes de novas páginas/lotes. O POST de transporte do Graph Batch não é mutação financeira.

## Cobertura e indisponibilidade

- Texto da conversa, contexto recente do canal, memórias e relatórios antigos servem para resolver intenção/período/metodologia, não como fonte financeira automática. Um reenvio só pode reproduzir um artefato cujas contas/publishers estejam comprovadamente no cadastro positivo; sem essa comprovação, reconstruir a leitura pelas fontes autorizadas. Não copiar valores de uma mensagem de outro agente para preencher lacunas.

- Reconciliar o conjunto esperado do cadastro com as linhas do resultado. Uma conta autorizada sem acesso pela credencial atual fica `unavailable`, com status/código, sem buscar outra operação e sem converter em saldo/gasto zero.
- Mostrar separadamente completude do recorte, contas efetivamente lidas e indisponíveis. Não declarar cobertura financeira total apenas porque o processo terminou com exit 0.
- Para validar a correção de escopo, exercitar a seleção genérica integral, uma leitura real por vínculo existente, paginação e as recusas offline. A recusa legítima da Meta é limitação de dados, não razão para ampliar fontes, permissões ou infraestrutura.
- Resposta de faturas vazia com HTTP 200 significa somente que a API não expôs faturas naquele recorte/período/identidade. Não prova ausência de faturas nem quitação. Atividade de cobrança, fatura e gasto publicitário são fontes distintas.
- Não publicar anexos ou payloads financeiros durante uma validação técnica; entregar status/cobertura e limitações. Um relatório financeiro efetivo informa período, moeda, fonte e unidade.

## Testes

Rodar no Python da instalação Hermes `tests/test_ares_scoped_report.py` junto de `test_ares_confidentiality_routes.py`, `test_mgs_ares_asset_scope.py`, `test_mgs_domain_scope.py` e `test_ares_meta_common_usage.py`. Os fixtures são sintéticos, nunca evidência de dado financeiro real.

## Referências públicas Meta

- `https://developers.facebook.com/docs/marketing-api/reference/ad-activity/`
- `https://developers.facebook.com/docs/marketing-api/reference/business/business_invoices/`
- `https://developers.facebook.com/docs/marketing-api/reference/omega-customer-trx/`
