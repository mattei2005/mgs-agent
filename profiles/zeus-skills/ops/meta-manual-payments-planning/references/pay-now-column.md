# Coluna Pay now das contas de linha

**Supersessão de letras:** por `1564022485366734969`, Pay now agora fica em **H**, após Invoice E e Setembro F. As menções a F/G/H abaixo documentam a implantação anterior; para execução atual prevalece `references/september-invoices.md` e o header live. Não inserir outra coluna Pay now. Ordenação humana é permitida: vincular ID/nome e descobrir a linha atual, nunca exigir o row_index antigo.

Autorização de Rodolfo: `1563981039230255186`, thread `1563926766286803004`. Leitura dos modais das 39 contas de linha da mesma aba, sem pagar, trocar cartão, preencher dados ou avançar Next. Nova F antes do antigo current balance; G agora balance e H gasto de outubro. Schema anterior fica explicitamente supersedido; não inserir outra F em ticks futuros.

## Regra atual: botão indisponível → balance do topo em H

Rodolfo `1564373157727576245` supersede a regra anterior que exigia modal em todos os targets. Na conta/BM autenticadas e corretas, Pay now explicitamente desabilitado/financeiramente indisponível significa usar em H o Current balance visível no topo (outubro ainda aberto), com pixels+AX e horário reais. Não clicar o botão, não publicar zero e não inventar modal. Guardar receipt `current_balance_pay_now_unavailable` e marcar a fonte na nota. O relato do dono explica a baixa das invoices; F/status continuam dependentes do amount_due live. Login/2FA, página incompleta, erro e bloqueio temporário de recurso Facebook não são indisponibilidade financeira. Pay now habilitado continua exigindo modal literal. Não reutilizar snapshot anterior como atual. Esta seção prevalece sobre menções históricas abaixo a “todos os modais” ou proibição genérica de balance em H.

## Cabeçalho do bloco de linha

Pedido `1563999324587819020`: repetir os oito títulos A:H na linha 13. O título de grupo LINHA DE CRÉDITO fica em A12, antes do cabeçalho repetido; contas e fórmulas não mudam de linha. No publisher, reconhecer cabeçalhos pela combinação A=Nome da conta/B=Forma de pagamento, e não somente i==0, para preservar também F13 em cada refresh. Não limpar essa célula como se fosse uma linha vazia ou uma conta fora do escopo.

## Execução exercitada

- `scripts/read_pc1_pay_now.py --account-ids <lote> --run-dir <dir>` abre aba própria, usa lease global PC1, navega nos links aprovados e clica somente no único Pay now da página inicial. Captura o modal Make a payment e extrai Amount you can pay now, Amount e Spending from. Não seleciona rádio/cartão, não edita valor e nunca clica Pay now final ou Next. Escape fecha o modal; finally fecha só a aba criada e libera lease.
- Descobrir o interpreter pelo launcher Hermes atual, não pelo checkout lembrado; executar o collector com esse Python. Batches de seis cabem no foreground, stdout somente resumo sanitizado. Nunca subagente/writer paralelo/39 abas simultâneas.
- `scripts/publish_pay_now.py --prepare` cria run_dir, targets de linha live, snapshot e candidato de superfície Chrome. Candidato é apenas hint: o collector exige fresh list_windows para provar que o mesmo handle ainda é Chrome vivo, cria aba própria e a captura do Meta correta é verificada antes de publicar. Se a janela autorizada saiu, não adivinhar outra nem afirmar logout global. Título é da aba ativa e pode mudar para assunto não Meta; isso não invalida por si só o Chrome já validado. Não inspecionar/interagir com conteúdo de abas preexistentes.
- Ler de fato cada `*-modal.png` com vision_analyze, confrontando business_id, asset_id e Amount com o receipt e target. Não usar filename como prova da URL. Erros de OCR de IDs não se normalizam por inferência ou lookup: recortar a barra nativa com region antes do resize, tipicamente [350,15,1050,65] em captura 1456×791, ou mais estreito quando necessário. Ampliar uma faixa panorâmica inteira causou novo downscale e piorou o OCR; o crop nativo resolveu.
- Após a leitura positiva de todos os screenshots, gravar `visual-verification.json` no run_dir com verified_account_ids exatamente iguais aos 39 targets, método e horário reais. Essa lista não substitui inspeção visual; nunca marcar sem fazê-la. API/nome do cartão default não fornecem este valor.
- `scripts/publish_pay_now.py --run-dir <dir>` faz plano sem escrever. Com `--apply` publica só F, com lock, backup, notas, totais e readback integral. `--insert-column-if-needed` ficou restrito à migração inicial autorizada; NÃO é necessário em execução recorrente. Se um insert tiver resposta ambígua, reconciliar header e snapshot antes de repetir, jamais inserir cegamente.
- `scripts/refresh_workbook.py --apply` agora resolve headers e atualiza C/E/G/H, preservando F e D. `scripts/record_pc1_proof.py` mantém escrita só D, mas verifica toda A:H. O validador verifica E/F/G/H, todas as 47 IDs e links; F é numérica em 39 linhas e vazia nas oito contas de cartão. Totais de F só no bloco linha e geral; subtotal cartão fica vazio, não zero inventado.

## Integração a cada tick 3x/dia

Aos 08:02/14:02/21:02 America/New_York, o job existente `2ee720363d7d` deve, além do ciclo de API e instrumento de cartão em recurring-refresh.md, executar prepare → collector em lotes dos 39 targets → inspeção dos 39 screenshots/manifest → publish --apply → refresh API --apply → validador. Não reutilizar a fotografia de uma execução anterior como se tivesse acabado de ler o modal. Honrar horários individuais nas notas porque a leitura é sequencial; não prometer que a soma estará simultaneamente pagável ou que o emissor terá limite.

Caso lease/auth/UI bloqueie uma conta, preservar a fotografia anterior e declarar quais campos ficaram históricos. Nunca completar lacuna com balance/Insights ou marcar atualização integral. Nenhuma etapa de cobrança é autorizada.

## Recuperação parcial explícita e validação de duas fontes

- O collector aceita página Billing válida com Credit line e balance explícito, mesmo quando o Pay now cinza está omitido pelo AX. Produz receipt `current_balance_pay_now_unavailable` sem clicar; isso é candidato até inspeção dos pixels. Login/erro/`temporarily blocked` interrompem a rota; não contornar limitação do provedor com outro perfil/endpoint de UI.
- No manifest visual, `disabled_balance_checks[account_id]` exige `pay_now_visually_disabled=true`, `valid_billing_page=true`, `business_id`, `asset_id` e `balance_usd` realmente conferidos. A ausência de Button no AX sozinha não autoriza publicação. Fonte e hora originais ficam na nota de H.
- Se um bloqueio do provedor interromper o conjunto, `publish_pay_now.py --run-dir <mesmo-dir> --verified-only --apply` publica somente os receipts já conferidos e preserva valores/notas de todos os targets faltantes. Totais e header qualificam a mistura de leituras novas/históricas. Sem `--verified-only`, o gate de conjunto completo permanece. Nunca chamar uma entrega parcial de atualização integral.
- `validate_workbook_readonly.py` valida as duas fontes de H, IDs, links e fórmulas; seu PASS prova a estrutura/snapshot, não a atualidade dos H preservados. `test_pay_now_sources.py --run-dir <dir>` exercita receipts reais e rejeições de prova ausente, valor/ID divergente e botão acionável.
- `Meta HTTP500/code1/subcode99`, erro de child batch e divergência de Insights são estados distintos: não inventar causa única. Manter recibos, verificar a mesma conta/período por GET diário/agregado, repetir somente leitura de forma limitada e publicar API apenas após reconciliação. A recuperação de API não remove bloqueio de UI.

## Reautenticação reaparece durante a coleta

- Tratar “já autentiquei” como gatilho para validar a mesma sessão, não como prova de liberação de todas as contas. Mesmo após modais válidos, a navegação seguinte pode redirecionar para `/security/twofactor/reauth/` e pedir “Enter the 6-digit code” sem um Heading `Confirm it's you`; inspecionar URL final e texto completo antes de classificar um timeout como falha de billing ou captura.
- Se pixels e AX confirmarem esse gate, distinguir autenticação inicialmente funcional de nova reautenticação pendente. Não alegar logout global, não tentar códigos por CUA, não tocar credenciais e não publicar cobertura parcial como completa. Preservar as leituras verificadas no mesmo run_dir e manter H anterior até completar o conjunto exato de targets.
- Para handoff humano, abrir apenas uma aba própria no Chrome aprovado com o destino exato, verificar o gate e liberar a lease. Informar a tela e pedir autenticação nessa mesma aba, sem solicitar código em chat. Na retomada, reconciliar os receipts existentes, coletar só os targets faltantes e validar todos antes de publicar.

## Prioridade de entrega

Publicar o resultado pedido assim que as leituras e validações essenciais estiverem prontas; não manter os valores coletados invisíveis enquanto se desenvolve infraestrutura auxiliar. Primeiro o pedido e readback; depois fechar o mínimo de compatibilidade/registro, sem ampliar o trabalho. Rodolfo corrigiu a demora na mensagem `1563992655468429466`.

Primeira publicação: 39/39 modais conferidos; soma USD 195514.29. Fonte histórica (não dado corrente): `reports/meta-pay-now-1563981039230255186/`. CPV-04-G003 mostrou USD 7312.05. A causa da diferença contra balance continua não comprovada; esta leitura não a transforma em invoice anterior.
