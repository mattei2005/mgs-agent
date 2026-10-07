# Setembro/2026 — complemento pessoal SMS no cartão de remuneração

## Autoridade e resultado

Implementação autorizada por Rodolfo em `1557413116793331774`, encaminhada para a thread financeira `1545426987756298340` em `1557413749881839758`. Origem: `1557406793603358742`. Decisão externa: `docs/finance-sms-personal-complement-1557407360509546527.md` e registro `FINANCE-SMS-PERSONAL-COMPLEMENT-1557407360509546527`.

Estado técnico: publicação `sms-personal-card-1557413116793331774` confirmada pelo controlador, journal `committed`, hashes locais/remotos e readback autenticado. O complemento existe somente na apresentação do cartão de setembro/2026 de Kelly/G005, Isliago/G003 e Joe/G004.

- Valor da comissão: `card_summary.remuneration.due.brl`, dinâmico e respeitando piso/faixa.
- Valor do reembolso SMS: fixo em centavos BRL — Kelly 201261, Isliago 154264, Joe 47456; total R$4.029,81.
- Total a receber: payable do mesmo payload + complemento, sem carry nem saldo de Pagamentos.
- Texto explícito: pago pessoalmente por Rodolfo e Geizian, fora do resultado financeiro.

Nenhuma alteração em despesa, rateio, lucro, cálculo de comissão, cash/payroll engine, ledger, pagamentos ou Sheets. Nicolas e Ícaro mantêm seu cartão original. Outras competências não herdam a apresentação. Detalhes preexistentes de piso, percentual e progresso permanecem.

## Readback atual — revisão setembro 1123

Valores verificados em produção, não copiados de prints:

- Kelly: comissão R$3.623,24 + reembolso R$2.012,61 = R$5.635,85.
- Isliago: comissão R$12.640,68 + reembolso R$1.542,64 = R$14.183,32.
- Joe: piso/payable R$3.000,00 + reembolso R$474,56 = R$3.474,56.

Comissão e total continuam acompanhando a Dash; os valores acima são um snapshot e não um congelamento.

## Modelo e preparação

Runtime PID528562 / sessão `20261007_113216_0eda44`: provider `openai-codex`, alias `gpt-6-astra-900k`, wire model `gpt-6-astra`. O resolvedor da instalação efetiva consultou o catálogo autenticado live: janela efetiva e `max_context_window` de 872000 tokens. Sem mudança de modelo global, credencial ou gateway. Evidência `model-runtime.json`.

Candidato source-only separado preparado por `deploy/prepare_release.py`, allowlist SHA256 e admissão compartilhada: 400 arquivos, 81.379.944 bytes; suplemento exato de closure existente, hash-verificado sob a mesma admissão. Nenhum código ativo foi editado antes dos testes. Comparação completa confirmou zero arquivos ativos ausentes e somente dois deltas de código.

## Arquivos e publicação

- `apps/finance-system/public/operations.js`: UI local e `public/operations.js` do release remoto.
  SHA256 `e2435e5ee31cb2539bd38506c85f3e71a03cc5d393fcff7fe5ac8fe687274d27`.
- `apps/finance-system/tests/manager-layout.test.mjs`: regressão local.
  SHA256 `959446c99f93c179dd4f5bf42793b21d2dd3328be274078af231a2121130e9d7`.

`finance_release.py check` e `finance_release.publish` executados sem contornar gate, manifesto, locks ou fence. Três destinos, arquivos já existentes. Somente `mgs-finance-dash.service` remoto foi reiniciado. Serviço, socket e PostgreSQL ativos no RunCloud. Journal/rollback: `apps/finance-system/private/releases/sms-personal-card-1557413116793331774/`.

## Testes realmente executados

- Sintaxe Node e regressão focada: 9/9 PASS.
- Gate Node completo: 263/263 PASS, zero skips/falhas/cancelados/todo; 397,383266s.
- Gate Python completo: 206 PASS, sem skips; 623,571980s.
- `npm audit`: zero vulnerabilidades.
- Stage real isolado PGlite + aplicação candidata + APIs autenticadas: 72 verificações desktop1440/mobile390. Owner preview e cinco manager shells reais de teste; igualdade de API owner/manager e bloqueio de gestor estrangeiro. Cartões não-alvos iguais ao markup antigo após serialização DOM equivalente.
- Stage com assets candidatos e APIs produtivas autenticadas, somente leitura: 30 verificações.
- Produção publicada: 30 verificações, repetidas após ajustar a captura para enquadrar o próprio cartão; asset público autenticado com SHA256 esperado. Zero erros JS, falhas same-origin, overflow de página/cartão/texto ou POST financeiro nos browsers.
- Screenshot mobile do cartão verificado visualmente: os três valores e a origem pessoal estão legíveis, sem corte horizontal.

Stage utilizou o cálculo real para FX5,5 e inválidos5%, exclusivamente em banco/memória isolados. Reembolso manteve seu valor nos dois cenários, enquanto payable/total acompanharam o engine. Exemplo de Joe: baseline piso3000 +474,56 =3474,56; FX alterado payable3215,38 +474,56 =3689,94. Nenhuma mudança de taxa/status em produção.

## Preservação e concorrência reconciliada

Fingerprints por hash de cada linha antes da agregação; não houve agregação de documentos completos. No cutover, todos os fingerprints antes/depois foram idênticos:

- 204 cenários: `31a3b88e96715dee558d1c67e3446290`.
- 29 entradas ledger: `30c79a131164880f22e4f43e221c200d`.
- 40 documentos históricos: `caf61e2fdb1d9cbece875c69af666d30`.
- 85868 source_cells: `d87687d3f15dd833ab9966a699365ecd`.
- 1 import: `098075f7b1a22f78156b048d36a310ce`.

Após o cutover, a rotina autorizada de câmbio registrou `AUTO_QUOTES_UPDATED`3336/3337, setembro1122→1123 e outubro277→278. USD/BRL4,95297→4,948812 e USD/CAD1,42569→1,42582163. A origem foi reconciliada com inventário/política de cotações e audit financeiro; não é anomalia nem lançamento desta release. As adições nominais permaneceram iguais, as únicas entradas alteradas foram as duas cotações e o restante dos cenários foi provado idêntico substituindo apenas os hashes desses dois registros pelo snapshot inicial e recuperando exatamente o fingerprint original. Fingerprint final dos cenários: `db991a03b10e9a4147243a755fb32439`; demais quatro conjuntos idênticos.

Não se declara API financeira byte-identical entre revisões cambiais diferentes. O payable/total visual mudou corretamente com a atualização automática. `preservation-final.json` contém a reconciliação e os hashes.

## Backup e recuperação

Dump PostgreSQL real: `/home/zeus/mgs-finance-backups/sms-personal-card-1557413116793331774/finance-before.dump`, cópia local em evidência. 111780787 bytes; SHA256 `eb6e561f3625305fb969b851ab152254397ab066a680ef62172168e41e7838b5`. `pg_restore --list` válido e cópia com hash idêntico. Não foi declarado restore materializado deste dump. Rollback de código exato está no journal canônico; nenhum backup foi excluído.

## Intercorrências resolvidas

1. `hermes-agent` desabilitada no tool: leitura direta da skill e código da instalação real, sem habilitar/configurar Hermes.
2. Comando documental `checkpoint` inexistente: corrigido para o subcomando canônico `checkpoint-upsert`.
3. Preparação inicial excedeu96MiB ao juntar a closure: gate preservado, retomada com allowlist original e suplemento exato previsto no runbook, sem cópia recursiva ou relaxar limite.
4. Diretório remoto de backup pertence à hierarquia protegida: primeira criação como zeus recebeu permission denied; criado via sudo com umask restritivo, sem alterar permissões/proprietários existentes.
5. Comparação inicial de string HTML contra outerHTML falhou por serialização de atributos/nbsp: normalização DOM equivalente, reexecução integral do stage72 PASS.
6. Fingerprint pós-browser inicialmente divergiu: investigação identificou e reconciliou exatamente os dois eventos normais de câmbio; nenhum dado foi corrigido artificialmente para forçar igualdade.
7. Primeira captura móvel não enquadrava a remuneração: scroll ao cartão e nova validação produtiva completa; captura final verificada.

Nenhum blocker de produção remanescente. Não se promete ausência de falhas futuras.

## Continuidade

Checkpoint: `ZEUS-FINANCE-SMS-CARD-1557413116793331774`. Evidência privada: `apps/finance-system/private/sms-personal-card-1557413116793331774/`, incluindo modelo, allowlist, gates, stage, manifest, published, runtime-final, preservation-final, screenshots, backup e receipts de comunicação. Aprendizado desta apresentação incorporado à referência documental canônica existente, sem criar/editar skills ou duplicar routers nesta execução one-shot.
