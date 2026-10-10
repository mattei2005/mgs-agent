# Navegação do gestor e proposta de resultado anual

Fonte: Rodolfo `1558488813536288789`, thread `1545426987756298340`.

## Decisão confirmada

- Renomear somente o menu **Minha visão** para **Dashboard** nas contas `manager` e na prévia correspondente.
- Preservar **Pagamentos**.
- Não transformar a visão do gestor em Dashboard empresarial: manter `/operations?view=manager`, a role e seus dados próprios, sem nova permissão ou cálculo.
- Rodolfo pediu uma visão do rendimento do ano e solicitou uma sugestão de desenho. A composição/implementação anual ainda precisa ser apresentada e alinhada; não publicar métricas financeiras novas por inferência.

## Proposta ainda não publicada

Nome recomendado: **Resultado Anual**, entre Dashboard e Pagamentos.

- Seletor de ano.
- Dois totais distintos: **Lucro líquido gerado** pelo gestor e **Minha remuneração** (salário/comissão devida conforme a regra de cada mês). Não confundir remuneração devida com pagamento registrado.
- Evolução mensal em gráfico simples e lista janeiro–dezembro com lucro gerado e remuneração; BRL/USD respeitando o câmbio da própria competência.
- Meses fechados preservam seus valores históricos. Mês em andamento mostra realizado até o corte disponível, identificado como parcial; nunca somar projeção ao acumulado. Meses sem dados/futuros ficam indisponíveis, não zero presumido.
- Somente dados do próprio gestor, com controle no servidor. Não liberar o endpoint ou os dados do Caixa Sintético empresarial para criar essa tela.
- Pagamentos permanece como local de saldo, lançamentos e recebimentos. Não duplicar ali a gestão de pagamentos.

Essa proposta não é uma alteração ativa das regras de remuneração nem uma publicação de novo menu. Confirmar com Rodolfo se deseja ambos os conceitos de rendimento antes da implementação anual.

## Execução do rótulo

Checkpoint `ZEUS-FINANCE-MENU-1558488813536288789`; evidências `apps/finance-system/private/manager-menu-1558488813536288789/`. **Rótulo publicado e validado**, release `manager-menu-1558488813536288789` committed:270 testes Node +220 Python,32 verificações de stage e14 produtivas desktop/mobile; hashes e fingerprints preservados. Relatório `reports/finance-manager-menu-1558488813536288789.md`. A proposta anual acima permanece pendente de alinhamento, sem novo menu/API publicado.
