# Despesas: cobranças por data e exclusões com vigência

## Autoridade
- Rodolfo1553037003099209738: retirar legenda, múltiplas cobranças desde setembro2026, cinco exclusões desde agosto.
- Confirmação1553040522287784077 do desenho apresentado; thread1545426987756298340.
- Rodolfo1553050044813283478: Ferramenta ver artigos desde setembro2026.

## Resultado verificado
- Publicação coordenada `expense-charges-1553040522287784077`, estado committed, hashes local/remoto confirmados. Arquivos workspace.mjs, public/app.js, public/refinements.css, testes workspace e GAM. Publicação de código sem escrita financeira.
- Desde setembro2026, cobranças com data/valor, +, remoção e total único por despesa. Servidor soma decimais exatamente e rejeita datas impossíveis/fora do mês, componentes inválidos, conflito de revisão e tentativa de uso em agosto. Moeda única por despesa, conversão preexistente. Legacy conserva valor sem inventar data. Conferência é independente; arquivamento/restauração conserva componentes.
- Agosto mantém editor de valor único. Legenda Despesa extra removida da listagem sem alterar origem interna.
- Desde agosto: company|125 ubbersuggest seo, company|128 Wire fee FB, company|130 uptimerobot, company|132 pagcorp, company|134 sendgrid arquivadas com USD/BRL zero.
- Desde setembro: company|122 Ferramenta ver artigos arquivada, agosto preservado.
- Todas17competências existentes agosto2026–dezembro2027 alteradas em transações/revisões independentes, recovery bloqueado, audit e readback. Futuro onboarding deve respeitar a vigência documentada; não há competências registradas além de dezembro2027 nesta execução.

## Testes e readback
- 208Node +162Python =370 testes, zero falhas/skips após recuperação.
- HTTP real em base isolada: criar duas cobranças, somar, ignorar total adulterado, editar/remover componente, persistir/reabrir, 400 inválido, 409 stale revision, conferência separada, arquivar/restaurar, agosto inalterado.
- Playwright isolado1440/390: criar/salvar/reabrir/alterar/remover, total120.30 CAD e posterior50, sem duplicação, sem erro JS/overflow.
- Produção: API autenticada leu17meses; UI1440/390 comprovou agosto legado, setembro múltiplo, total de prévia, data legado vazia, rodapé acessível, legenda ausente. Nenhuma cobrança fictícia salva em produção. Logout401 e health autenticado OK.
- Query final: zero erros financeiros ativos,17audits de arquivamento e209cenários anteriores fora do escopo com hash inalterado. Agosto foi editado concorrentemente por Rodolfo (audits2243,2244,2248 EXPENSE_UPDATED); preservado, não tratado como anomalia.

## Falhas recuperadas
- Teste inicial vermelho esperado antes da implementação; testes de integração passaram após implementação.
- Suite Python identificou quatro expectativas antigas da autoridade GAM anterior. Alinhadas à regra WavesBee já publicada, sem mudar o código/regra GAM produtivo;162Python passaram.
- Primeira inspeção visual encontrou rodapé cortado no celular; scroll interno corrigido, retestado e reinspecionado. Cabeçalho e botões ficam inteiros.
- Primeiro smoke público tentou ler summary.counts inexistente na projeção pública. Corrigido apenas o harness para shape real; erros financeiros confirmados por SQL persistido, smoke repetido com sucesso.

## Evidência, rollback e retenção
Diretório privado: `apps/finance-system/private/expense-charges-1553040522287784077/`.
- candidate/private/gates/{node,python}-result.json, stage-browser.json, stage-{1440,390}.png.
- manifest.json, published.json, publish-financial-{before,after}.json.
- archive-{stage,production}-apply-*.json, preservation-final.json, production-browser.json, production-{1440,390}.png.
- backup/backup.json contém caminhos e hashes do dump nas duas máquinas; backup/restore.json e ensaio17meses comprovam restauração em mgs_finance_charges_1553040522287784077.
- Código de rollback do controller em private/releases/expense-charges-1553040522287784077. Recuperação financeira deve usar cenário recovery-archive-1553040522287784077-AAAA-MM e revisão/ID, jamais sobrescrever todo o banco por cima de edições novas.
- Base isolada e runtime /home/zeus/mgs-finance-stage-charges-1553040522287784077 retidos como evidência, sem daemon auxiliar. Nenhuma exclusão destrutiva, mudança de credenciais, permissões, Sheets ou gateway.
- Fonte canônica atualizada: docs/finance-company-expenses-order.md. Skill: references/company-expense-source-order.md.
