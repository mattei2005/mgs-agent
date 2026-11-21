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

## Inventário por criação/agendamento e extração de tracking

Este ramo cobre campanhas criadas em uma janela e/ou com início em outra, seguido da lista de UTMs para cadastro. Não usar `ares-scoped-report.py inventory` como se retornasse campanhas: esse modo projeta apenas metadados da conta. Usar os helpers comuns de GET/Graph Batch, sem alterar executor, credencial ou campanhas durante o relatório.

1. **Resolver janela e seleção antes de HTTP.** Consultar o relógio real e fixar datas civis e fuso do pedido. Para cada conta do catálogo positivo, exigir `mgs-ares-asset-scope.py check-account <ID> --json` com `allowed=true` e resolver o item corporativo pelo contrato atual da conta/operação. Separar explicitamente ausência de binding, recusa remota e coleção vazia; não transformar nenhum deles em zero campanhas. Agrupar contas por binding real, não pelo token que conseguiu ler outra família. Respeitar o reader gate vigente quando aplicável.
2. **Validar identidade em lote.** Pedir `account_id,name,business{id},timezone_name` por `act_<ID>` com `graph_batch_get`. Confirmar identidade e BM antes de ler filhos. Não fazer auth check individual seguido de outra leitura idêntica em cada conta quando o batch de identidade já fornece essa prova. Persistir uma linha de cobertura por conta, inclusive indisponíveis, antes de avançar o lote.
3. **Paginar campanhas leves.** Pedir `id,account_id,name,created_time,start_time,status,effective_status,objective` em `act_<ID>/campaigns`, com `limit=100` e os estados aceitos documentados na skill. Em cada filho bem-sucedido, validar `account_id`, acumular por ID e seguir o cursor `after` no mesmo path até esgotar páginas. Salvar lotes médios e retomar somente contas/páginas ausentes; nunca usar a URL autenticada de `paging.next` como destino arbitrário.
4. **Formar a união em código.** Converter cada timestamp para o fuso fixado, selecionar `created_time` dentro da primeira janela OU `start_time` dentro da segunda e deduplicar por ID. Excluir terminais do conjunto de agendamento e preservar o estado no inventário de criação. Não confundir início configurado com veiculação habilitada: campanha pausada com data futura tem apenas início configurado. Se o pedido for sobre conjuntos novos em campanhas antigas ou a data de campanha não bastar, ler `adsets{id,campaign_id,start_time,status,effective_status}` no recorte relevante; o início da campanha não representa necessariamente todos os seus conjuntos.
5. **Ler tracking somente dos alvos selecionados.** Consultar `<campaign_id>/ads` em batches bounded com `id,status,effective_status,adset_id,creative{id,url_tags,object_story_spec}` e paginar integralmente. Deduplique creative IDs e consulte `asset_feed_spec` somente para esses IDs quando precisar verificar destinos dinâmicos; extraia `link_urls` sem persistir vídeos, imagens e textos desnecessários. Nos links de `object_story_spec`, cobrir `link_data.link` e `video_data.call_to_action.value.link`. Ler só `url_tags` perde operações que instalam o tracking na Website URL; ler só a Website URL perde tags adicionais e variantes AFS.
6. **Validar e projetar antes de salvar.** Resolver os hosts reais dos destinos e passar cada um no checker de domínio. Persistir apenas a projeção permitida: campaign/ad/creative/adset IDs, estados, host validado, origem do campo e `utm_campaign`/`utm_adgroup`. Não salvar links de hosts recusados, tokens, `paging.next` nem o payload criativo integral. Parsear com `urllib.parse` e preservar os valores literais; nunca completar zeros ou fabricar `g01`. Comparar os valores de Website URL, `url_tags` e variantes AFS; conflito, campo ausente ou macro não resolvida vira pendência explícita, não escolha silenciosa de um valor.
7. **Consolidar e apresentar.** Agregar em código por domínio, estratégia e chave, mantendo associação com campaign IDs e estados para auditoria. Um valor repetido em vários anúncios entra uma vez no bloco de cadastro. Não repetir a campanha por pertencer às duas janelas e não afirmar ausência de BOT ou de novas campanhas nas contas não lidas. Informar primeiro janela/fuso, campanhas únicas, subconjunto agendado e cobertura; depois entregar os blocos completos do formato Iris, sem anexos não solicitados. Fora dos blocos, sinalizar pausas ou pendências de anúncio relevantes, sem transformar o inventário em uma nova execução de campanha.

### Aceite da extração

- Reconciliar por conjuntos os IDs esperados e coletados de contas e campanhas; HTTP 200 do outer batch não prova sucesso de seus filhos.
- Exigir coleções de anúncios não vazias antes de usar `all(...)`; coleção vazia não comprova tracking validado.
- Validar igualdade das UTMs entre anúncios/variantes que devem compartilhar tracking e permitir múltiplos valores somente quando comprovados pela estrutura real da campanha.
- Somar as contagens deduplicadas por domínio e verificar que cada valor entregue tem pelo menos uma origem lida e um host aprovado; preservar as associações mesmo quando os blocos omitem IDs técnicos.
- Testar os casos de sobreposição de datas, paginação, valores repetidos, zeros literais, ausência de AFS, destino AFS divergente, macro não resolvida e conta indisponível. Fixtures não provam leitura live.
- Declarar cobertura parcial quando houver conta sem binding, grant ou paginação completa; entregar a parte comprovada sem chamar o pedido global de integralmente concluído.

## Cobertura e indisponibilidade

- Texto da conversa, contexto recente do canal, memórias e relatórios antigos servem para resolver intenção/período/metodologia, não como fonte financeira automática. Um reenvio só pode reproduzir um artefato cujas contas/publishers estejam comprovadamente no cadastro positivo; sem essa comprovação, reconstruir a leitura pelas fontes autorizadas. Não copiar valores de uma mensagem de outro agente para preencher lacunas.

- Reconciliar o conjunto esperado do cadastro com as linhas do resultado. Uma conta autorizada sem acesso pela credencial atual fica `unavailable`, com status/código, sem buscar outra operação e sem converter em saldo/gasto zero.
- Mostrar separadamente completude do recorte, contas efetivamente lidas e indisponíveis. Não declarar cobertura financeira total apenas porque o processo terminou com exit 0.
- Para validar a correção de escopo, exercitar a seleção genérica integral, uma leitura real por vínculo existente, paginação e as recusas offline. A recusa legítima da Meta é limitação de dados, não razão para ampliar fontes, permissões ou infraestrutura.
- Resposta de faturas vazia com HTTP 200 significa somente que a API não expôs faturas naquele recorte/período/identidade. Não prova ausência de faturas nem quitação. Atividade de cobrança, fatura e gasto publicitário são fontes distintas.
- Para setembro/outubro por conta, filtrar também `billing_period` no retorno e separar competência de emissão; uma invoice emitida em outubro pode pertencer a setembro. Não confiar apenas nos filtros de data do request. Exigir `Unpaid`/`Partially Paid` para a lista em aberto e vínculo positivo de todas as contas; não ratear invoice multi-conta sem detalhamento comprovado.
- Manter gasto Insights, valor integral da invoice (`amount`) e saldo residual (`amount_due`) como grandezas distintas. Nunca preencher invoice com o gasto do mês: ajustes de faturamento podem produzir diferenças reais. A normalização monetária exige offset/documentação da moeda; não inferir o saldo residual a partir de `balance`. Se o guard recusar `amount_due` ou `billed_amount_details`, não contornar nem ampliar o guard dentro do relatório; entregar os campos autorizados com a limitação explícita. Outubro em andamento não é invoice emitida só por existir gasto.
- Não publicar anexos ou payloads financeiros durante uma validação técnica; entregar status/cobertura e limitações. Um relatório financeiro efetivo informa período, moeda, fonte e unidade.

## Apresentação por conta e forma de pagamento

Para o relatório Digital Trust de setembro/outubro com invoices abertas, reunir todas as contas selecionadas em somente dois blocos, `Cartão` e `Linha`, nas colunas `Conta → Invoice → Setembro → Outubro → Forma de pgto`. Não subdividir por presença/ausência de invoice. Reformatar a mesma base validada sem nova coleta quando o pedido mudar somente o layout; manter semântica, horário e ressalvas dos valores. Verificar unicidade das contas e reconciliação dos subtotais após reagrupar.

## Testes

Rodar no Python da instalação Hermes `tests/test_ares_scoped_report.py` junto de `test_ares_confidentiality_routes.py`, `test_mgs_ares_asset_scope.py`, `test_mgs_domain_scope.py` e `test_ares_meta_common_usage.py`. Os fixtures são sintéticos, nunca evidência de dado financeiro real.

## Referências públicas Meta

- `https://developers.facebook.com/docs/marketing-api/reference/ad-activity/`
- `https://developers.facebook.com/docs/marketing-api/reference/business/business_invoices/`
- `https://developers.facebook.com/docs/marketing-api/reference/omega-customer-trx/`
