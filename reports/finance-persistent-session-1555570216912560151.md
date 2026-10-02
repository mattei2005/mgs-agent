# Sessão persistente e atualização automática — publicação validada

Autoridade: Rodolfo `1555570216912560151`, após pedidos `1555568204607135796` e `1555569927891718275`; thread `1555563097375383643`.
Política ativa: `docs/finance-persistent-session-update-notice.md`.

## Resultado

- Login persistente para todos, sem logout idle3h/absoluto8h; cookie seguro400dias renovável e sessão PostgreSQL infinity. Migração apenas de sessões antigas ainda válidas, nenhuma sessão expirada/revogada reativada. MFA, senha, roles, CSRF e revogação preservados.
- Atualização automática compartilhada: dados sem reload completo; estrutura com restauração de contexto por aba; consulta30segundos e retorno ao foco. Dialog aberto, formulário alterado e operação/requisição em curso adiam a atualização e mostram tarja. Nenhuma gravação financeira é repetida pela atualização.
- A instalação inicial exige recarregar uma vez abas abertas com o código antigo. Limpeza/modo anônimo/políticas do navegador podem encerrar a persistência; não se promete login literalmente eterno.

## Provas executadas

- TDD: teste de cookie persistente falhou no código anterior, passou depois. Regressões cobrem31min/179min/181min/25h/60dias, migração válida, legacy idle expirado, absoluto legacy expirado, revogação, CSRF, assets privados, MFA e papéis.
- Gates completos:240Node +188Python =428, sem skips/falhas. Auditoria de dependências produtivas:zero vulnerabilidades.
- Stage HTTPS/PGlite isolado com snapshot real de setembro:17checks desktop1440/mobile390. Mudança de revisão lida; dados não navegam; mudança real no hash de CSS seguida de restart do servidor de teste causa exatamente uma recarga e restaura view/mês/filtros/rolagem. Editor com valor digitado permanece intacto; perfil inline alterado também. Requisição real retida impede refresh. Falha de fetch injetada preserva dados/pendência e recupera depois. Zero erro JavaScript e zero POST financeiro.
- Publicação pelo controlador canônico:18destinos (10locais/8remotos), manifest/prova de stage/gates/readback; cutover80.223s. Somente serviço financeiro reiniciado. Nenhum gateway, PostgreSQL, firewall ou unit foi modificado.
- Fingerprints por documento de cenários/revisões/resultados/overrides/additions, ledger e auditoria financeira iguais antes/depois do cutover.
- Browser produtivo autenticado com senha+MFA de Rodolfo:28checks em desktop/mobile, APIs de versão e saúde, Dashboard/Relatório/Despesas/Pagamentos/Perfil/Conferência/Julho/Histórico e previews administrativos dos cinco gestores. Zero erro JavaScript e zero POST financeiro. Cookie seguro e persistente >399dias; fechar/reabrir contexto com cookie mantido não pediu login.
- Registro produtivo da sessão de teste confirmado com persistent=true/revoked=false; ao final, somente essa sessão foi encerrada e401confirmado. Os testes não contornaram o MFA de outros usuários.

## Arquivos e recuperação

- Código: `auth.mjs`, `server.mjs`, `public/navigation.js`, `public/navigation.css`, `public/app.js`, `public/operations.js`, `public/history.js`, `public/review.js`.
- Regressões: `tests/auth.test.mjs`, `tests/self-profile.test.mjs`.
- Evidência: `apps/finance-system/private/persistent-session-1555570216912560151/`: `baseline.json`, `manifest.json`, `stage.json`, `candidate/private/gates/*-result.json`, `dependency-audit.json`, `published.json`, `publish-financial-before.json`, `publish-financial-after.json`, `production-browser.json`, `production-session.json`, `backup.json`.
- Dump: `/home/zeus/mgs-finance-backups/persistent-session-1555570216912560151/finance-before.dump`; SHA256 `1324c011ab51e9abbecb0bd9ab56be051ac1be760392d9c5d89f152ae9d44108`, catálogo pg_restore validado.
- Código anterior/journal: `apps/finance-system/private/releases/persistent-session-1555570216912560151/`.
- Backups e evidências preservados. Nenhuma exclusão solicitada/executada. A sessão infinity exige a consideração específica de rollback documentada na política; não restaurar o banco inteiro para reverter UI/auth.

## Falha de teste corrigida e prevenção

A primeira execução de stage contava `framenavigated` como recarga; Playwright também emite esse evento para `history.replaceState`, produzindo um falso positivo. O contador passou a contar requisições reais de navegação do frame principal. Os17checks finais passaram; teste de reload estrutural ainda exige exatamente uma navegação real, sem enfraquecer o critério. Não houve falha ou indisponibilidade produtiva nessa correção.

O auditor da skill ainda exigia a antiga política3h/8h e inicialmente reprovou a supersessão correta. Foi atualizado para exigir persistência, elegibilidade segura da sessão legacy e guards do refresh, repetido com39Markdown PASS e sincronizado por hash. No registro institucional, o helper recusou superseder uma proposta em draft (aceita somente predecessores ativos); readback confirmou que nenhuma entrada parcial foi criada. A decisão automática foi então registrada como a única ativa de sua chave, preservando a proposta antiga como draft histórico e a supersessão explícita no documento. A política anterior ativa de sessão foi supersedida atomicamente. Validação institucional final:zero erros.

Escopo financeiro preservado: nenhuma mudança de regra/cálculo, receita/gasto, remuneração, liquidação, pagamento, catálogo, fonte Sheets ou histórico financeiro.
