# Sessão3h, rateio parcial e DicasFinancas — publicado e validado

Autoridade: Rodolfo `1551947602562392085`, thread `1545426987756298340`.

## Resultado

1. Inatividade de sessão ampliada de30min para3h nas duas consultas de `auth.mjs` (renovação e reutilização). Limite absoluto8h, cookies, MFA, papéis, exclusividade da Conferência e redirecionamento ao login preservados. Não foram trocadas credenciais nem revogadas sessões de terceiros.
2. Linhas diárias parciais agora mostram Despesas Gerais e Funcionários pelo mesmo rateio mensal/dias da competência. Esses custos compõem lucro e ROI da linha. O TOTAL REALIZADO continua somando apenas dias completos; dias futuros vazios permanecem zero. No recorte por site, mantém-se somente seu rateio de Despesas Gerais, sem criar rateio adicional de funcionários. Valores mensais, folha e cotas existentes não foram alterados por esta correção de apresentação.
3. Mapeamento permanente: `dicasfinancas` → `dicasfinancas.info`, BR, `br-cc-br`. Medium ausente retorna a G002/MGS com a regra de sufixo existente; o complemento concreto usou `g002-s`. Medium canônico explícito de outro gestor prevalece, coberto por regressão.

## Catálogo e complemento financeiro

- Site ausente no catálogo financeiro produtivo; criado como `dicasfinancas.info`, ID `site-dicasfinancas-info`, Rede1/CAD, MGS, nas16competências setembro/2026–dezembro/2027. Entrada sem participação no rateio (`INATIVO`/Não participa), preservando cotas e valores existentes; este atributo financeiro não afirma inatividade do site web/campanhas.
- Rehearsal real de setembro aprovado; aplicação em lotes limitados, revision guards, recovery imutável por competência e readback do alvo. Fatos preexistentes e valores/cotas/folha preservados em cada registro. Agosto e históricos não foram editados.
- Setembro: cadastro517→518; complemento518→519, audit1867. Importada somente a parcela CAD `0.018550884640459408` em21/09, `g002-s`, `br-cc-br`.
- Fonte integral21/09:3035 linhas→59grupos; CAD `28798.31949953348322594333`, USD `6913.927141529553880181`. Zero blockers, cutoff21/09, receita e gastos do mesmo dia completos.
- Reexecução da fonte exata: `already_applied`, revisão519 inalterada e sem novo audit financeiro. State final `ok`, `failure_streak=0`, flags de intervenção limpos.

## Validação real

- TDD: os testes de31min de sessão e rateio no dia parcial falharam antes das mudanças; ambos passaram depois. A nova regressão DicasFinancas também foi primeiro vermelha, depois verde.
- Gate completo:196Node +128Python =324 testes, sem skips. Sessão válida com31min/179min, inválida com181min; expiração absoluta e revogação permanecem testadas.
- Stage:27probes de autenticação/redirect/API e17competências financeiras. Para testar o estado parcial real, foi capturado o snapshot produtivo anterior ao complemento e usado em leitura isolada; não foi fabricada uma resposta de API.
- Browser público autenticado:34combinações período/viewport (17competências × desktop1440/mobile390), zero erro JavaScript e zero POST financeiro. Setembro21 completo com ambos os custos rateados,22futuro zerado, ausência de banner parcial. Cinco APIs de gestores responderam200; Conferência manteve6itens, sem alerta. Navegação anônima continua indo ao login; API anônima401.
- Replay do snapshot parcial real na função JavaScript efetivamente publicada comprovou rateio em21/09 ainda parcial e TOTAL REALIZADO limitado a20/09, sem dupla contagem.
- Readback produtivo: hash exato dos5arquivos publicados; duas condições idle3h, antiga idle30min ausente, absoluta8h presente. Socket, aplicação e PostgreSQL ativos. Na fase de publicação de código, fingerprints de cenários/ledger foram idênticos; alterações financeiras posteriores ficaram limitadas aos cadastros e ao complemento autorizado.

## Backups e fontes

- Trabalho/evidência: `apps/finance-system/private/session-rateio-dicas-1551947602562392085/`.
- `before/`, `before-local-hashes.json`, `backup.json`, `code-backup.json`: cópias locais, dump validado e tar remoto anteriores, com hashes/rollback preservados.
- `gate/`, `test-counts.json`, `stage-result.json`, `browser-production.json`, `live-policy-hashes.json`, `catalog-source-readback.json`, `register-apply-*.json`.
- Apply: `private/gam-email-runs/20260922T094347-0400/result.json`; replay: `private/gam-email-runs/20260922T095141-0400/result.json`.
- Recovery catálogo: `recovery-dicasfinancas-1551947602562392085-YYYY-MM`; complemento: recovery do importador registrado no resultado apply.
- Regra executável: `data/finance-gam-revenue-rules.json`; fonte institucional: `docs/finance-gam-email-automation.md`; skill `mgs-finance-dashboard` e referências de autenticação/sequência atualizadas com supersessão.

## Falhas transitórias recuperadas

-09:31, cron detectou hash do runner local diferente do remoto ainda não publicado;09:41, runner novo encontrou DicasFinancas ainda sem cadastro. Ambos pararam no preflight. O cadastro foi concluído, manual-intake reaplicou a mesma fonte e recuperação integral/idempotência foram validadas. Alerta foi explicado na thread. Prevenção persistida: preparar todo o pacote isoladamente e ativar regra/código local/remoto somente depois de catálogo e runner prontos, sob locks.
- Stage distinguiu0de-0 em asserção estrita e usava fixture anterior sem o novo dia parcial. Normalizada somente a comparação de zero e acrescentado snapshot real de produção; probes repetidos e aprovados, sem enfraquecer o gate.
- Primeiro lote de edição de skill foi abortado atomicamente por uma operação sem mudança; lote corrigido/reaplicado e lido de volta. Nenhuma regra financeira foi alterada para contornar um teste.

Sem alteração de Google Sheets, despesas mensais, regras de salário/comissão, câmbio liquidado, pagamentos, histórico imutável ou credenciais. Nenhum gateway foi reiniciado.
