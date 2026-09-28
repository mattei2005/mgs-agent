# Conferência mensal — descontos por rede e site

- Autoridade: Rodolfo `1553399478248017973`; thread `1545426987756298340`.
- Estado: **publicado e validado em produção**.
- Escopo: visualização somente leitura; nenhum lançamento, política de desconto, cadastro, conta, credencial, campanha ou regra financeira alterados.

## Resultado

Os detalhes dos quatro blocos de receita — Rede1 CAD, Rede2 USD, AV USD e M2 USD — mostram Gross, Tráfego inválido, Rev share e Líquido, tanto no total da rede quanto por site. O valor principal do cartão permanece gross. Facebook e Google preservam gastos e detalhamento original, sem descontos de monetização inventados. O líquido da rede não é lucro final: não deduz impostos, mídia e demais custos operacionais.

Reutilizados os valores calculados salvos na competência. Não se aplicam taxas atuais sobre períodos anteriores. A projeção na moeda original segue o fator comum efetivamente aplicado pelo motor a cada fato; rev share é a diferença residual entre líquido, bruto e inválidos, com aritmética decimal inteira. Os valores originais não são modificados. Ausência de cálculo confirmado permanece pendente. Valores são arredondados apenas para apresentação; uma diferença de um centavo entre linhas individualmente arredondadas não cria um ajuste financeiro.

M2 agosto/2026 validado na API e na interface:
- Gross: USD4.611,87.
- Tráfego inválido: −USD102,31.
- Rev share: −USD225,48.
- Líquido: USD4.284,08.

## Validação real

- Gates integrais: **381 testes aprovados**, sendo214 Node e167 Python, sem skips/TODOs/cancelamentos.
- Comparação em17 competências reais: retirando apenas os novos campos de desconto, a resposta permanece idêntica à anterior; nenhuma mutação do snapshot de entrada.
- Somatórios de site/rede por moeda e identidade gross + inválidos + rev share = líquido validados em precisão decimal.
- Staging e produção:17 competências em34 visualizações desktop/móvel em cada fase; todos os valores de cada rede/site comparados à API, sem overflow horizontal, sem erros JS, sem POST financeiro.
- M2 USD4284.08 confirmado no navegador produtivo nos dois tamanhos.
- Fingerprints de todos os cenários antes/depois do cutover idênticos: revisões, resultados, overrides e additions preservados.
- Hashes dos arquivos locais e remotos validados pelo publicador canônico; saúde autenticada aprovada.
- Gastos e GAM reconsultados: `ok`, contadores de falha0, concluídos até25/09/2026; não houve novo processamento financeiro nesta alteração.

## Ocorrências recuperadas em homologação

- Primeiro gate Python encontrou fixture privada ausente: `private/origin-1546618148571058266/production-before.json`. Foi restaurada a cópia real, sem alterar o teste, e a suíte integral foi repetida e aprovada.
- Primeiro teste de navegador redimensionou uma página desktop com o menu aberto para móvel, deixando o overlay sobre os detalhes. O harness passou a recarregar a página após definir a viewport, respeitando a inicialização normal da navegação; staging e produção passaram integralmente. Não foi alterada a navegação produtiva.
- Não houve incidente produtivo nem escrita financeira durante esses testes.

## Artefatos e reversão

- `apps/finance-system/simple-review.mjs`
- `apps/finance-system/public/review.js`
- `apps/finance-system/public/review.css`
- `apps/finance-system/tests/simple-review.test.mjs`
- Direção canônica: `docs/finance-system-product-direction.md`.
- Skill do profile Zeus: `mgs-finance-dashboard/references/preventive-release-gate-and-review.md`, com regra de apresentação e aprendizados de fixture/harness.
- Evidência privada: `apps/finance-system/private/review-deductions-1553399478248017973/` — `stage-financial.json`, `browser-stage.json`, `browser-production.json`, `publish-financial-before.json`, `publish-financial-after.json`, `published.json`, manifest e screenshots.
- Backup/rollback controlado: `apps/finance-system/private/releases/review-deductions-1553399478248017973/`; sete arquivos before registrados no journal.
- Serviço de aplicação reiniciado pelo controlador de release; worker financeiro não reiniciado. Nenhum gateway de agente reiniciado.

Inventário, audit log, registry e checkpoint acompanham esta entrega; REPORT-INFRA direto no canal canônico e verificado por readback. Nenhuma pendência funcional da alteração.
