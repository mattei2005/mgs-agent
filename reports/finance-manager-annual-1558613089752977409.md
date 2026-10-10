# Resultado Anual individual — publicado e validado

Autoridade: Rodolfo `1558613089752977409`, thread `1545426987756298340`. Contrato canônico: `docs/finance-manager-annual-result.md`. Release `manager-annual-1558613089752977409`.

## Entrega

- Novo menu **Resultado Anual**, entre Dashboard e Pagamentos, para Ícaro, Isliago, Joe, Kelly e Nicolas; também funciona na prévia exclusiva de Rodolfo.
- Seletor de ano existente, R$/US$, cartões separados de lucro líquido gerado e remuneração devida, evolução mensal e quadro janeiro–dezembro.
- Apenas realizado; mês atual parcial até o corte disponível. Futuro não vira zero. Remuneração não significa recebimento; reembolsos/saldos não entram no acumulado.
- Cada mês preserva sua fonte e moeda/câmbio. A tabela soma os centavos exibidos, sem alterar precisão dos registros. Histórico consulta versões ativas existentes, nunca uma nova leitura de Sheets.
- APIs existentes já restritas ao próprio gestor; nenhuma mudança de backend, schema, role, credencial, MFA ou permissão. Caixa Sintético empresarial continua bloqueado.

## Cobertura histórica explícita

Nos cinco gestores, a origem de janeiro/fevereiro não fornece o consolidado do resultado no padrão posterior (Ícaro possui salário sem aba própria nesse início). Essas duas competências ficam com resultado indisponível e explicação — não foi inventado zero nem consolidado retroativo. A remuneração histórica dessas competências continua disponível.

Na validação de 2026, cada gestor apresentou **8 meses de lucro disponível e 10 de remuneração**, incluindo outubro parcial; novembro/dezembro futuros indisponíveis. A tela mostra a cobertura junto aos acumulados. Isso é um limite dos dados de origem preservados, não falha de consulta nem tarefa financeira autorizada pendente.

## Evidência executada

Diretório privado: `apps/finance-system/private/manager-annual-1558613089752977409/`.

- Candidato source-only isolado; alterações exatas em `public/navigation.js`, `public/operations.js`, `public/operations.css` e `tests/navigation-profile.test.mjs`.
- Regressões novas: realizado versus estimativa; devido versus comissão/recebimento; futuro/sem dias completos; histórico com câmbio próprio e resultado negativo; ausência versus zero; total de centavos e cobertura; menu/isolamento.
- Gates completos: **274 Node +220 Python**, sem falhas, cancelamentos ou skips. Durações 369.039524s e624.511898s. `all-result.json` real preservado byte a byte nos nomes esperados pelo controller.
- Auditoria npm:115 dependências, zero vulnerabilidades reportadas. Skill audit:41 documentos PASS; não é auditoria integral da contabilidade.
- Stage: **36 verificações**;20 combinações de cinco gestores ×desktop/mobile ×sessão TEST normal/prévia,15 negativas de acesso e1 falha transitória/recovery.12 linhas mensais, ambas as moedas, fontes mensais reais, comparação de totais, navegação Dashboard/Pagamentos, reload e ausência de overflow. Snapshots reais em banco isolado; nenhuma sessão de terceiro criada em produção.
- O teste deliberado de HTTP503 inicialmente propagou a rejeição esperada ao harness. O harness passou a consumir essa rejeição e toda a etapa foi repetida: a UI oculta o acumulado antigo, permite retry e recupera os dados. Não foi falha induzida em produção.
- `finance_release.py check` PASS; `publish` committed em7 destinos (4 locais e3 remotos). Hashes exatos; app/socket/PostgreSQL ativos. Somente o serviço financeiro recarregado. Nenhum gateway ou banco reiniciado.
- Produção: **12 verificações finais** em1440/390px — dez combinações dos cinco gestores e dois controles de Geizian. Conferidos todos os meses disponíveis, moedas, cartões/total, bloqueios403 de empresa/outro gestor, prévia, reload e Pagamentos intacto. Zero erros JS, falhas HTTP de UI ou POST financeiro. Repetido após a atualização concorrente de câmbio descrita abaixo.
- Login real de Rodolfo com MFA existente; sessão de validação revogada no fim e retorno401 inclusive com seletor de prévia. Sessões, MFA e confiança dos demais usuários preservados.

## Concorrência financeira reconciliada

Os fingerprints das seis tabelas verificadas eram **idênticos imediatamente antes/depois do cutover**. Durante o primeiro canário, a rotina autorizada de câmbio atualizou setembro e outubro, eventos financeiros3868/3875 (`AUTO_QUOTES_UPDATED`, ator `Zeus / cotação automática`): setembro1236→1237 e outubro403→404. A diferença de override foi somente `principal|Agosto 2026|H1`; adições nativas e demais inputs nominais ficaram idênticos. Os resultados derivados acompanharam esse câmbio normal. Não alegar identidade integral do documento financeiro depois dessa rotina independente.

Cadastro, ledger, histórico e dispositivos confiáveis continuaram idênticos. Mudança de MFA do proprietário corresponde ao uso normal dos logins de teste, não reset/alteração de segredo. Evidência: `financial-validation.json`, `security-readback.json`. A release realizou zero escritas financeiras; o canário foi reexecutado contra as novas revisões e passou.

## Backup, rollback e resíduos

Backup remoto `/home/zeus/mgs-finance-backups/manager-annual-1558613089752977409/` contém arquivos anteriores e dump custom. Catálogo pg_restore e segunda cópia local por hash conferidos; não foi alegado restore materializado. Controller mantém journal e backups exatos em `private/releases/manager-annual-1558613089752977409/`. Rollback é dos arquivos, sem mudança financeira. Gates/evidências privadas preservados; nenhuma limpeza destrutiva autorizada ou executada.

## Continuidade

Decisão `FINANCE-MANAGER-ANNUAL-1558613089752977409`, checkpoint `ZEUS-FINANCE-MANAGER-ANNUAL-1558613089752977409`, skill `mgs-finance-dashboard`. Inventário e REPORT-INFRA com readback obrigatório antes do encerramento. Não há decisão ou ação técnica pendente do usuário nesta entrega.
