# WavesBee, despesas e explicação de origem

Autoridades Rodolfo:1553019425706217652 (WavesBee),1553021450158342275 (três exclusões e CAD40),1553021574402015365 (pergunta sobre legenda),1553029057153728553 (Adspower membro extra). Thread1545426987756298340.

## Resultado

- WavesBee principal `wavesbee.com` US/us-cc-en e Finanzas `finanzas.wavesbee.com` US/us-cc-es, ambos Isliago/G003, permanentemente separados. Alias `wavesbeefinanzas` registrado. Cadastro financeiro novo `site-wavesbee-finanzas`/WavesBee Finanzas, setembro2026–dezembro2027, Rede1/CAD, sem acrescentar cota ao rateio. Medium canônico explícito continua prevalecendo.
- Fonte GAM24/09:3000linhas→58grupos. CAD33673.06509297804855478367 e USD8104.3400871613600962897. Somente CAD0.012742353809102358/g003-d foi complementado;57grupos prévios preservados. Revisão678, audit2192, último dia completo24/09; replay already_applied e state ok/zero blockers/failure_streak0.
- Despesas agosto2026–dezembro2027: `company|109`, `company|131`, `company|141` arquivadas (Topveiw AI dif de cobranca, wordfence premium plugin, SB LeadsOn Hub); `company|143` SB Wire Fee40CAD. Setembro2026–dezembro2027: `company|119` Adspower membro extra arquivada. Excluir utiliza semântica nativa reversível, sem remover histórico.
-17transações auditadas2196–2212, com recovery bloqueado por competência. Agosto já possuía parte das edições de Rodolfo; foram preservadas, inclusive AdsPower e as despesas nativas `SB Wire Fee usd:`. Nenhum pagamento, cobrança externa, conta, campanha ou Sheet alterado.
- Legenda `Despesa extra`: `public/app.js`/expenseView a exibe quando `extra=true`, indicando cadastro nativo. O lançamento entra uma vez no cálculo. Não foi autorizada nem executada mudança visual.

## Validação

-369testes de release,207Node+162Python, zero skips; ensaio GAM real com delta1, fontes/totais preservados, novo catálogo pronto antes da regra.
- Release coordenada `wavesbee-1553019425706217652`, hashes local/remoto lidos de volta, backup de código e invariância financeira durante publicação. Nenhum gateway reiniciado por esta tarefa.
- Backup PostgreSQL com cópia local/remota e hashes iguais, restore real em duas bases isoladas: `mgs_finance_wavesbee_1553019425706217652` e `mgs_finance_expenses_1553021450158342275`.
- Ensaio de despesas em todas17competências e canário apply/verify isolado de agosto/setembro. Produção alterada sob admissão/locks, revisão guardada e readback por mês.
- Preservação final17/17: overrides, fatos diários, catálogo, corte e additions fora dos IDs autorizados iguais aos recoveries imediatamente anteriores. Alterações do próprio Rodolfo foram reconciliadas via audit financeiro.
- HTTPS autenticado:17competências × desktop1440/mobile390 =34views. Ausência das despesas arquivadas na lista ativa, CAD40, taxa USD10 preservada onde existente, legenda explicada, GAM58grupos e ausência do banner parcial. Zero JS/overflow/POST financeiro. Health autenticado passou; logout e401 confirmados.
- Na conferência final, setembro revisão679, corte24/09. Auditorias financeiras por autoridade/período confirmam cada escrita exatamente uma vez.

## Diagnósticos e recuperação segura

- Primeiro gate de candidato falhou por fixtures privadas/deploy ausentes, antes de publicação. Copiados os recursos reais necessários; ambos gates repetidos integralmente e aprovados, sem excluir testes.
- Primeira conexão ao restore foi recusada pelo pg_hba para mgsfinance em base isolada; nenhum SQL de mutação ocorreu. Refeito pelo peer mgs_pg com cópia privada do código em `/home/zeus/mgs-finance-stage-expenses-1553021450158342275`; sem alterar pg_hba/permissões produtivas. Apply e replay isolados passaram.
- Recibo local interrompido foi reconciliado com SELECT/audits:12meses já haviam sido aplicados. Somente os5faltantes foram executados; nenhum commit duplicado.
- Python do ambiente Hermes não tinha openpyxl. Uso explícito do `/usr/bin/python3` validado resolveu sem instalação ou mudança de config.

## Evidência e continuidade

Raiz: `apps/finance-system/private/wavesbee-1553019425706217652/`.
Arquivos: `published.json`, `stage-gam.json`, `catalog-registration.json`, `apply-result.json`, `replay-result.json`, `expenses-audit-readback.json`, `preservation-final.json`, `browser-production.json`, backups e recibos por competência.
Release/rollback de código: `apps/finance-system/private/releases/wavesbee-1553019425706217652/`.
Backups/restore/stage retidos e inventariados; nenhuma exclusão destrutiva de evidência autorizada.
Mapeamento e política de despesas persistidos em docs canônicos e referências da skill mgs-finance-dashboard. Não prometer prevenção de desconhecidos novos; país/domínio novo continua fail-closed.
