# Resultado Anual individual do gestor

Autoridade: Rodolfo `1558613089752977409`, após confirmação explícita dos dois valores na thread `1545426987756298340`; proposta original `1558495235930062860` e pedido `1558488813536288789`.

## Escopo aprovado

- Menu **Resultado Anual**, entre **Dashboard** e **Pagamentos**, para os cinco gestores e sua prévia read-only já autorizada.
- Seletor de ano; lucro líquido gerado e remuneração devida em totais separados; evolução e resumo janeiro–dezembro; BRL/USD conforme a própria competência.
- Não confundir resultado da operação, remuneração devida e recebimento. Pagamentos permanece intacto.
- Meses históricos usam a versão ativa congelada da própria aba e a remuneração histórica já exposta ao gestor. Não aplicar regras atuais ao passado. Ausência de consolidado original fica explícita e não vira zero.
- Meses nativos usam o resultado realizado e remuneração atual do próprio gestor, não estimativas. Mês atual/competência incompleta identificado como parcial. Futuro ou mês sem dias completos: indisponível.
- Somar somente valores disponíveis e mostrar cobertura: acumulado parcial nunca se apresenta como ano integral. Conversões usam o câmbio do próprio mês, não o último câmbio aplicado ao total anual.
- Apenas consultas já autorizadas ao próprio gestor, com isolamento no servidor. Nenhuma liberação de Caixa Sintético ou financeiro de outra pessoa. Não alterar credenciais, MFA, sessões alheias, regras financeiras, pagamentos, banco ou Sheets.

## Estado

**Publicado e validado.** Release `manager-annual-1558613089752977409` committed;274 testes Node +220 Python,36 verificações isoladas e12 finais em produção desktop/mobile, cinco gestores e Geizian como controle. APIs próprias e Pagamentos preservados; nenhum write financeiro da release. Rotina concorrente de câmbio reconciliada nos eventos3868/3875 e canário repetido nas novas revisões. Relatório `reports/finance-manager-annual-1558613089752977409.md`; evidências `apps/finance-system/private/manager-annual-1558613089752977409/`; checkpoint `ZEUS-FINANCE-MANAGER-ANNUAL-1558613089752977409`.

Na cobertura2026 validada: lucro disponível março–outubro (8meses) e remuneração janeiro–outubro (10meses), incluindo outubro parcial. Janeiro/fevereiro não têm o consolidado original no padrão posterior e ficam explicitamente indisponíveis, nunca zero; remuneração histórica preservada. A tela identifica a cobertura do acumulado. Novembro/dezembro futuros não entram na soma.

Esta decisão/publicação supersede somente o alinhamento pendente da proposta em `docs/finance-manager-navigation.md`; o rótulo Dashboard anteriormente publicado permanece válido.
