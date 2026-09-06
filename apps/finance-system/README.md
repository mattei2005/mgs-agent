# MGS Finance — aplicação própria em homologação

Autorização: Rodolfo, Discord `1545900695545192479`, thread `1545426987756298340`.

## Hospedagem protegida adicional

A descrição local abaixo é o marco histórico inicial. A hospedagem inicial com gate 503 (1545928620462313645) foi supersedida pela confirmação crítica 1545934831664242748: `https://dash.mgsdigitalcorp.com/login` está publicada com PostgreSQL 18 e login rodolfo. Estado/recuperação atuais: `deploy/PG-AUTH-RUNBOOK.md`; histórico do gate: `deploy/README.md`. Banco/login passaram, mas a migração funcional integral e a substituição da planilha NÃO estão concluídas.

## Estado e limites

Aplicação **real e executável**, com PostgreSQL embarcado (PGlite), backend Node/Express e motor determinístico Python Decimal. Local-only: nenhuma conta, assinatura, credencial produtiva, firewall, systemd ou fonte Google foi modificada. Não representa conclusão da migração funcional integral e não substitui a planilha.

### Camadas implementadas

- Captura auditada imutável e verificada por SHA-256; nova leitura Google independente para freshness.
- 9 abas financeiras das 6 planilhas, 406 precedentes históricos explicitamente congelados, sem USUARIOS BOT.
- Grafo de migração recursivo: resultados esperados nunca entram no cálculo. Referências e spills calculados, ciclos/gramática desconhecida bloqueados, cotações externas identificadas como inputs provisórios.
- Primitivas financeiras nativas: receita/invalidos/rev-share/imposto/ROI, projeções calendárias, conversões, despesas, piso e faixas de comissões; caixa derivado.
- Adaptadores de origem para 43 segmentos e 78 combinações segmento-país; descrições ligadas pela fórmula de origem, nunca pela ordem das linhas do dashboard.
- Aplicação com visão geral, caixa, sites/países, diário, gestores, despesas/pessoal, entradas/regras, reconciliação e audit.
- Cenários imutáveis após congelamento, edição numérica com recálculo, lançamentos novos independentes de células, propagação a comissão/pessoal/caixa para gestores mapeados. SEM_COMISSAO deve ser escolhido explicitamente para não comissionados.
- PostgreSQL persistente, revisão otimista, transação em cada alteração, audit append-only, importação idempotente, readback.
- UI com escaping, API parametrizada, limites de payload, bloqueio de Host/Origin, CSP. **Não são substitutos de autenticação corporativa**: bind somente 127.0.0.1.

### Cobertura que ainda NÃO está concluída

- CRUD completo de cadastros, contratos e versões por vigência, inativação futura e abertura de períodos. A tabela `entity_versions` reserva o modelo, mas não comprova esses fluxos implementados.
- Migração restante do grafo de compatibilidade para regras/cadastros sem coordenadas; entrada operacional ampla e importadores de reports.
- Definição de estados de aprovação, liquidação real, conciliação externa e fechamento produtivo.
- Autenticação/roles de aplicação, domínio/TLS, banco de produção, backup externo, observabilidade e cutover.
- Lançamentos nativos adicionais entram no consolidado nativo e nas comissões, mas não têm equivalentes celulares; a grade histórica do Caixa e detalhes importados continuam identificados como reprodução da planilha, não como ledger nativo completo.

Não converter PASS de agosto em afirmação de equivalência funcional completa. A meta integral permanece aberta. Não tratar uma nova aba de Google Sheets como entrega.

## Executar

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

`npm test` prova importação idempotente, paridade, edição/retorno, isolamento do baseline, criação nativa, revisão, bloqueio de fechamento, Host/Origin, persistência por reabertura e restore de dump PGlite. Evidências ficam em `private/integration-evidence.json` e `private/browser-evidence.json`.

## Dados e recuperação

Todo `private/`, `node_modules/` e caches ficam fora do Git. `source.json` e seu hash são preservados; não reimportar com o mesmo ID se o conteúdo mudou. Backups de teste de restauração são locais, não disaster recovery externo. Preservar os diretórios de teste até gate de limpeza autorizado; exclusão exige Critical Subset.

Para rollback de código, não alterar Sheets. Parar somente o processo local da aplicação, preservar banco/dumps e retornar a uma revisão previamente validada. Nunca executar restart do gateway do Zeus.
