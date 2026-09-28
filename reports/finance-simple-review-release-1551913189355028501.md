# Conferência simples e corte dos gestores — publicação validada

Autoridade atual: Rodolfo `1551913189355028501`, confirmação adicional ao bloqueio de corte. Autoridades anteriores preservadas: `1551798771661275147` (apresentação simples) e `1551811440418095186` (primeiro preenchimento vazio). Thread `1545426987756298340`.

## Resultado publicado

- `https://dash.mgsdigitalcorp.com/review.html`: apenas seis itens do mês selecionado — gross CAD Rede1; gross USD Rede2; gross USD AV; gross USD M2; gastos Facebook; gastos Google. Valores em moedas originais, detalhes de composição disponíveis, sem transformar despesas/pessoal/vigência em tarefas manuais adicionais. Não representa aprovação/liquidação do mês nem conciliação externa automaticamente concluída.
- Correção do primeiro preenchimento de receita em campo vazio publicada. Continua usando o allowlist do modelo e a guarda de entradas do Workbook.
- Motor alinha o rateio, a projeção e as bases dos gestores ao último dia explicitamente completo. Data de execução real continua registrada. Receitas/gastos posteriores permanecem como fatos nominais parciais, fora da base completa dos gestores até avanço legítimo do corte. Não avançar corte artificialmente.
- Corrigidas as cinco APIs de gestores. Conferência de soma por site versus total permanece ativa, não suprimida.

## Diagnóstico e desenho

A virada Eastern alterava TODAY/rateio, embora `data_cutoff` permanecesse20/09. Além disso, totais mensais importados podem vir de um spill que ignora o subtotal diário local. `financial_cutoff.py` prepara somente uma cópia do grafo: clock financeiro cutoff+1, folhas diárias de gestores posteriores vazias e totais monetários importados recompostos dos mesmos dias. Não modifica source.json, fórmulas de origem, taxas, regras de comissão ou entradas persistidas. `worker.py` filtra a contribuição de fatos nativos posteriores ao corte na base do gestor, sem descartá-los do relatório geral.

## Publicação e readback

- Sete arquivos funcionais publicados por hash: simple-review.mjs, monthly-review-routes.mjs, public/review.html, public/review.js, public/review.css, worker.py e financial_cutoff.py.
- Revisão setembro510→511, recálculo exclusivo de `workspace-2026-09`, com auditoria `MANAGER_CUTOFF_ALIGNED`, autoridade1551913189355028501. Corte permaneceu20/09. Entradas, additions e fatos nominais idênticos; demais cenários e finance_ledger idênticos por fingerprint antes/depois sob locks de importação/cotações.
- Alterações concorrentes494→510 foram reconciliadas como `AUTO_QUOTES_UPDATED`, não anomalia.
- Serviço, socket e PostgreSQL ativos no host financeiro RunCloud. Gateway Hermes não reiniciado. Nenhuma alteração de credencial, permissão, billing, systemd ou Sheets.
- Login owner real via1Password+MFA; sessão de teste encerrada e revogação401 validada.

## Evidência de testes

- Gate fail-closed atual:191Node +127Python, zero skips, manifestos iguais aos arquivos candidatos. Fixture real agosto validada por hash. Gates completos, não somente casos novos.
- TDD: regressões efetivamente vermelhas para virada de calendário, receita nativa parcial e receita legada parcial; green final na suíte127. Corte nulo, limite de dia completo e preservação do payload cobertos.
- Banco restaurado:17competências, owner permitido/partner e manager negados na conferência; cinco namespaces com guard aprovado; primeiro preenchimento outubro não altera setembro; correção setembro não altera outubro; formulário cruzado rejeitado. Dados sintéticos de setembro/outubro restaurados por fingerprint; recálculo autorizado do snapshot de teste preservado.
- Browser candidato e produção:17meses × desktop/mobile=34combinações por fase, seis itens na ordem, sem overflow/errosJS/POST financeiro/consultas técnicas desnecessárias. Na fase stage, dados vêm do PostgreSQL restaurado e o controle de gestores do ensaio remoto; produção verificou as cinco APIs públicas reais.
- Agosto recalculado em memória com worker anterior e atual: facts, managers, expenses, cash, realized e projection exatamente iguais. Isso complementa a preservação das outras competências no banco.

## Backup, recuperações e limites

Backup fresco de código e dump PostgreSQL, catálogo pg_restore e transferência porSHA256 validados. Paths exatos em `private/cutoff-1551913189355028501/backup.json` e `code-backup.json`; rollback mantém arquivos anteriores e cenário bruto. Não excluir banco restaurado ou evidências sem autorização crítica específica. Em commit incerto, consultar auditoria da autoridade antes de repetir.

O primeiro comando usou `python` inexistente; corrigido para `python3`. O gate Python foreground foi interrompido pelo teto externo420s, sem processo sobrevivente; reexecutado em processo silencioso acompanhado até exit0 em495.7s. Isso foi falha do harness, não falha produtiva. Os testes novos também expuseram spill de totais e um assert de vazio indevido; corrigidos antes da publicação. Nenhuma falha residual dessas verificações.

A conferência continua exibindo a exceção de origem já existente Fincgriffin/USD143,85 em setembro, sem reclassificação automática. Não é novo blocker de deploy nem comprovante de fechamento. Câmbio/invalidos/liquidação e fontes faltantes continuam sob regras vigentes.

## Artefatos

- `apps/finance-system/private/cutoff-1551913189355028501/`: backups, stage-cutoff.json, stage-result.json, browser-stage.json, published.json, recalculated.json, db-before/after-publish.json, browser-production.json, august-recalculation-parity.json.
- Gates: `apps/finance-system/private/simple-review-1551798771661275147/gate/`.
- Regressão de calendário usa a captura real preservada `private/simple-review-1551798771661275147/september.json`; materializar esse fixture privado em restores de desenvolvimento, nunca inventá-lo ou publicá-lo.

Este relatório supersede somente os estados de publicação bloqueada dos relatórios1551798771661275147 e1551811440418095186. Não encerra as evoluções institucionais ainda abertas do sistema financeiro.
