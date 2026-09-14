# MGS Finance — aplicação financeira em produção

Autorização: Rodolfo, Discord `1545900695545192479`, thread `1545426987756298340`.

## Estado de produção e desenvolvimento

O gate inicial 503 (1545928620462313645) foi supersedido pela confirmação crítica 1545934831664242748. `https://dash.mgsdigitalcorp.com/login` é a aplicação ativa, autenticada e apoiada por PostgreSQL 18 privado. Estado e recuperação: `deploy/PG-AUTH-RUNBOOK.md`; histórico do primeiro gate: `deploy/README.md`.

## Estado e limites

Produção usa PostgreSQL 18 via socket privado, backend Node/Express e motor determinístico Python Decimal. PGlite permanece somente como adaptador de testes isolados; executar localmente não replica credenciais, serviços ou dados produtivos. A dashboard não substitui as fontes canônicas de competências históricas e das regras que ainda dependem da planilha.

### Camadas implementadas

- Captura auditada imutável e verificada por SHA-256; nova leitura Google independente para freshness.
- 9 abas financeiras das 6 planilhas, 406 precedentes históricos explicitamente congelados, sem USUARIOS BOT.
- Grafo de migração recursivo: resultados esperados nunca entram no cálculo. Referências e spills calculados, ciclos/gramática desconhecida bloqueados, cotações externas identificadas como inputs provisórios.
- Primitivas financeiras nativas: receita/invalidos/rev-share/imposto/ROI, projeções calendárias, conversões, despesas, piso e faixas de comissões; caixa derivado.
- Adaptadores de origem para 43 segmentos e 78 combinações segmento-país; descrições ligadas pela fórmula de origem, nunca pela ordem das linhas do dashboard.
- Aplicação com visão geral, caixa, sites/países, diário, gestores, despesas/pessoal, entradas/regras, reconciliação e audit.
- Cenários imutáveis após congelamento, edição numérica com recálculo, lançamentos novos independentes de células, propagação a comissão/pessoal/caixa para gestores mapeados. SEM_COMISSAO deve ser escolhido explicitamente para não comissionados.
- PostgreSQL persistente, revisão otimista, transação em cada alteração, audit append-only, importação idempotente, readback.
- UI com escaping, API parametrizada, limites de payload, autenticação e roles, bloqueio de Host/Origin, CSRF, CSP, HSTS, Permissions-Policy e transporte por socket Unix privado atrás da borda pública.

### Delimitações atuais

- Fechamento, liquidação real, taxas efetivas, inválidos confirmados e decisões de cadastro/status continuam exigindo o fluxo financeiro aprovado; a automação diária não decide esses pontos.
- A planilha permanece fonte oficial para competências e regras híbridas ainda vinculadas a ela.
- Lançamentos nativos entram no consolidado e nas comissões, mas não têm equivalentes celulares; a grade histórica e os detalhes importados continuam identificados como reprodução da origem, não como um ledger nativo integral.
- Origin e systemd estão endurecidos. MFA individual é obrigatório para as sete identidades: Rodolfo está ativo via 1Password; Geizian e os cinco gestores devem concluir o QR individual no próximo login. Trust opcional dispensa somente TOTP por 30 dias no mesmo navegador, sem ampliar a sessão ou dispensar senha.

Não converter um PASS isolado em equivalência funcional irrestrita. Resolver estado técnico pelo runtime e pelo último relatório integral; não tratar uma nova aba de Google Sheets como entrega do sistema.

## Executar localmente para desenvolvimento/testes

```sh
cd /root/mgs-agent/apps/finance-system
npm ci
python3 import_snapshot.py
node server.mjs
```

Padrão `http://127.0.0.1:8765`; opcional `FINANCE_PORT` altera só a porta local. Não expor remotamente este ambiente sem aprovação e autenticação apropriada.

O importador requer as evidências auditadas originais no caminho declarado. Runtime não usa Google nem credenciais. `verify_live.py` usa exclusivamente o helper SA canônico e faz apenas GET.

## Verificação

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py'
npm test
node tests/browser.mjs
python3 verify_live.py
```

`tests/browser.mjs` usa Chromium já instalado 1234, sem alterar os profiles ou o Chromium 1228 protegido de outros agentes. Testes utilizam dados reais no baseline e valores sintéticos marcados TEST **somente** em cenários/DBs de teste. Resultados sintéticos não são reportados como finanças MGS.

As suítes Node e Python cobrem importação idempotente, paridade, edição/retorno, isolamento do baseline, criação nativa, revisão, bloqueio de fechamento, autenticação/Host/Origin/CSRF, cache por revisão, persistência por reabertura e recuperação isolada. Evidências operacionais ficam em `private/` e o último resultado consolidado fica no relatório integral registrado.

## Dados e recuperação

Todo `private/`, `node_modules/` e caches ficam fora do Git. `source.json` e seu hash são preservados; não reimportar com o mesmo ID se o conteúdo mudou. O DR off-site completo inclui profiles, MGS OS, código versionável da aplicação, fontes documentais registradas e dump PostgreSQL custom, criptografados antes do upload. O restore semanal valida hashes, ZIPs, bancos SQLite, conhecimento institucional e catálogo do dump PostgreSQL; um restore PostgreSQL materializado usa banco isolado e exige o gate destrutivo para seu descarte posterior.

Para rollback de código, não alterar Sheets. Parar somente o processo local da aplicação, preservar banco/dumps e retornar a uma revisão previamente validada. Nunca executar restart do gateway do Zeus.
