# Login — redirecionamento sem sessão corrigido

Autoridade: Rodolfo1551937825073790986, thread1545426987756298340. Complemento1551941818181095515 pede explicar o dia parcial; não autoriza nova classificação financeira ou alteração dos prazos de sessão.

## Publicação e causa

- Produção redirecionava apenas `/`; arquivos HTML protegidos como `/review.html?view=review&period=2026-09` recebiam401 JSON quando não existia sessão válida. Captura do usuário e fonte produtiva confirmaram o defeito.
- Publicado somente `auth.mjs`: navegação GET/HEAD aos caminhos raiz/index, operations, history e review, com ou sem extensão, retorna303 para `/login`, com no-store. APIs, assets e tentativas de escrita continuam401 JSON. Usuário desativado também é encaminhado ao login na navegação HTML.
- Não foram alterados credenciais, MFA, papéis, exclusividade da Conferência (`rodolfo` + `owner`), cookies, política de sessão ou dados financeiros.
- Fonte produtiva confirma expiração por30min sem requisição autenticada e limite absoluto8h. `last_seen` é renovado no máximo uma vez por minuto. Deixar a aba aberta/ler sem requisições não é atividade do servidor. Confiar30dias dispensa somente a etapa TOTP após senha correta; não estende a sessão. Os limites estão confirmados, mas não há evidência que identifique qual deles causou cada saída observada pelo usuário.

## Validação real

- Regressão inicialmente vermelha (`/index.html`:401 !=303); depois verde. Cobre sessão ausente, inválida, revogada, expirada por inatividade e expirada no limite absoluto; APIs preservadas.
- Gate completo:196 testes Node +127 Python =323, sem skips. Auditoria de dependências:zero vulnerabilidades.
- Stage:27 verificações GET/HEAD, páginas com query, cookies inválidos e401 de APIs/assets, além de login200.
- Browser público:10 navegações anônimas em desktop1440/mobile390 chegaram à tela de login, sem JSON ou erro JavaScript. Resposta original303/Location `/login`/no-store e API401 lidas diretamente. Login real de Rodolfo via1Password/MFA continuou válido; seis itens da Conferência carregaram. Logout da sessão de QA confirmado; não houve revogação das sessões de terceiros.
- Arquivo produtivo lido por hash; socket, aplicação e PostgreSQL ativos. Hashes agregados por linha de todos os cenários e ledger antes/depois idênticos. Zero escritas financeiras.
- Backup completo e tar anterior preservados, com hashes e rollback exato.

Evidências: `apps/finance-system/private/login-redirect-1551937825073790986/` (`published.json`, `db-before.json`, `db-after.json`, `stage-result.json`, `browser-production.json`, `session-policy-readback.json`, `gate/`, `dependency-audit.json`, `backup.json`, `code-backup.json`).

## Recuperações de harness, sem impacto produtivo

- `fetch` Node22 ignorou Host explícito no teste loopback, gerando403 do gate de Host. Echo HTTP comprovou Host recebido127.0.0.1 em vez do domínio aprovado. Trocado exclusivamente o probe por `node:http.request`; os27 checks passaram, preservando a segurança do aplicativo.
- Uma tentativa de upload chamou função inexistente; repetida corretamente pelo transporte tar/stdin do helper canônico e stage revalidado.
- A leitura SQL de diagnóstico encontrou string vazia em números opcionais. Repetida comNULLIF antes do cast; sem qualquer escrita.

## Explicação do dia21 parcial — leitura somente

Fonte: `data/finance-gam-revenue-state.json`, run `private/gam-email-runs/20260922T082818-0400/result.json`, screenshot e PostgreSQL produtivo revisão516/cutoff20/09.

- Relatório21/09:3035 linhas, das quais3034 classificadas/aplicadas em58 grupos. Confirmados CAD28798.30094864884276653533 e USD6913.927141529553880181.
- Uma linha `pl_digital-trust_dicasfinancas_br`/BR, CAD0.018550884640459408, segue pendente como `unknown_domain`, candidato `dicasfinancas.info`; o alias/vertical não foram confirmados nesta tarefa. O valor mostrado no alerta é CAD0,018551, não0,0018551.
- O dia21 aparece parcialmente no Relatório Diário; o TOTAL REALIZADO continua até20/09. Em `public/financial-summary.js`, somente dias completos recebem o rateio diário de Despesas Gerais e Funcionários. Assim, os dois zeros do dia21 não significam ausência de despesas; o resultado eROI dessa linha não são fechamento nem são comparáveis diretamente aos dias completos.
- Nenhuma regra de importação, tolerância, fato, rateio ou cutoff foi alterado para explicar a captura. A associação permanente do identificador e sua vertical continua pendente de confirmação financeira.
