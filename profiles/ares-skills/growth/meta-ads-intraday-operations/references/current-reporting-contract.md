# Contrato genérico de relatórios Meta Ads

Este arquivo define somente a apresentação e as evidências mínimas. Métricas, horários, thresholds e ações vêm do contrato da operação.

## Exceção ativa — SHEIN: delegar ao contrato específico

Para relatórios SHEIN, carregar `direct-traffic-shein-operations` e `references/canonical-report-renderer.md` daquela skill. Resolver o binding da thread e ler `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`, incluindo `account_report_overrides` e o perfil vigente, antes de coletar e novamente antes de entregar. Esta referência genérica não mantém uma segunda especificação ativa do layout SHEIN, pois cópias parciais ficam desatualizadas quando o contrato muda.

Não restaurar os modelos históricos de treze ou quinze colunas abaixo: o padrão específico inclui St, RPS visível da dash e B.R.% na grade uniforme, com ordenações independentes do principal e do histórico. Usar o renderer canônico sem flags de prévia em pedidos normais, validar o texto exato e entregar suas partes sem reescrita ou segunda paginação. Receita ausente permanece n/d; RPS não pode ser substituído por API ou fórmula. Nenhuma regra visual autoriza cron, write Meta ou exclusão de relatórios.

## Histórico supersedido — apresentação SHEIN anterior

Para pedido genérico de relatório de qualquer conta de anúncio SHEIN, independentemente de domínio, gestor, canal ou solicitante autorizado, usar **R/E → Início → Nº → Produto → Quiz → Gasto → Receita → Saldo → Est.Health → ROI → ROI est. → ROAS → Lance**, por decisão de Rodolfo na thread `1560303769680355525`. Esse layout específico prevalece sobre o conteúdo genérico abaixo e os antigos modelos de sete colunas. R/E mostra duas bolinhas independentes na ordem ROI real/estimado: a real mantém positivo 🟢, negativo 🔴, exatamente zero 🟡; a estimada usa <+10% 🔴, +10% a +40% inclusive 🟡 e >+40% 🟢; ausente/inválido ⚪ em ambas. Comparar sem arredondar; não representa ação ou status. Logo abaixo do principal, incluir histórico de ROI real por campanha para sete datas (dia do relatório + seis anteriores), mesmas campanhas/ordem, denominador Meta e hoje parcial marcado com horário/timezone, acrescentando `Média 7d` na extrema direita. Essa média é aritmética dos ROIs reais diários válidos, exclui n/d, mostra cobertura n/7 quando incompleta e indica * quando incluir o dia parcial. Pedido explícito diferente pode adaptar o relatório. Alinhamento SHEIN: centralizar cabeçalhos e células de todas as colunas do principal, exceto Produto à esquerda; histórico inteiramente centralizado, incluindo Média 7d. Respeitar largura visual Unicode das bolinhas. Usar separadores ` | ` (barra ASCII U+007C) entre todas as colunas no principal e no histórico, sem barras externas nem linhas horizontais; esse visual aprovado é o padrão SHEIN. Revalidar posições visuais e limite de cada mensagem após inserir as barras, preservando famílias e cobertura. Ordenação SHEIN: Produto A–Z, depois famílias por Início da origem (mais antigo primeiro), número/ID. Cada origem é seguida por suas cópias em bloco contíguo, com pai antes dos filhos e irmãos por Início/número/ID; essa regra prevalece sobre a ordenação plana por data. Histórico na mesma ordem. A política posterior `discord_pagination` usa o máximo de linhas completas até 2000 por mensagem, sem margem arbitrária nem quebra antecipada por família: preservar adjacência e ordem, permitindo continuação da família na mensagem seguinte. Entrega nativa por recibo exato validado, sem segunda paginação. Resolver COPY explícito com pai único do mesmo produto/conta, sem inventar vínculos e detectando ciclos. Na identificação Nº, acrescentar `COPY Cxx` quando explícito no nome atual verificado da campanha, preservando a origem direta; nunca inferir pela UTM nem renomear objetos Meta por essa apresentação. Fonte canônica: `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`; carregar `direct-traffic-shein-operations` e sua referência `smartbidding-product-analysis.md` para definições e coleta. Não ampliar permissões, períodos, filtros, automação ou domínio por essa regra de apresentação. Incluir também **⏱️ ATRASO GAM/SB** em destaque no cabeçalho, sem adicionar uma coluna: ler `totalMinutes` de `POST /estimated/delay` do Smart Bidding para o publisher real e registrar horário/escopo; sem leitura válida, `n/d`, não zero presumido. É atraso GAM informado pelo SB, não medição direta da API GAM. Fonte canônica: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout/gam_delay`; detalhes e testes na referência SHEIN.

### Produto compacto e sem legenda extensa — SHEIN

Produto deve ocupar no máximo **20 caracteres incluindo espaços, sem reticências acrescentadas**, sem quebra interna e com largura visual Unicode máxima de 20. O visual foi aprovado por Rodolfo e substitui o limite anterior de 25 com `...`. O truncamento só afeta a célula: manter o texto completo para identidade, ordenação e famílias, sem renomear Meta ou consolidar prefixos iguais. Não incluir legenda explicativa por padrão; somente rodapé conciso de fontes/fórmulas essenciais, parcial e limitações. O renderer lê essas regras atuais do contrato e deve ser validado antes da entrega.

### Gate SHEIN antes da entrega

Para as 36 threads Intraday, resolver o binding em `data/ares/discord/shein-intraday-report-bindings.json`, ler o contrato atual e executar `shein-report-layout.py render` e `validate` com `--thread-id`, conforme `direct-traffic-shein-operations/references/canonical-report-renderer.md`. Usar o texto gerado sem reescrever tabelas. Validação falha bloqueia publicação; corrigir localmente, não enviar versão parcial fora do padrão. Histórico da sessão não sobrepõe a regra atual. O helper é offline e não posta no Discord.

## Cabeçalho obrigatório

```text
<Alias da conta> — <dd/mm/yyyy> — <HH:MM timezone da conta> — <tipo do relatório>
Período: <início–fim> | Moeda: <currency> | Fontes: <Meta e fontes externas aprovadas>
Modo: <read_only | dry_run | controlled_write>
```

## Conteúdo mínimo por campanha

```text
Camp | Nome operacional | Status | Início | Spend | Métrica principal | Custo/resultado | Ação | Motivo
```

Regras:

- Usar o alias curto da conta no título; IDs técnicos ficam no audit.
- `Camp` usa o identificador humano definido pela operação; nunca inventar número ausente.
- `Início` é data real `dd/mm/yyyy` no timezone da conta.
- Status operacional vem do nível campanha; inconsistência de adset/ad aparece como observação quando relevante.
- Métrica principal e custo/resultado usam os nomes e fórmulas do contrato da operação.
- Em `read_only/dry_run`, a ação deve ser simulada: `observaria`, `manteria`, `pausaria`, `reativaria`, `criaria` ou `não agiria`.
- Em `controlled_write`, mostrar ação executada e resultado do GET/readback.
- Sem ação/erro, o cron pode ficar silencioso quando o contrato permitir.
- Quando houver receita/ROI externo, declarar atraso da fonte, moeda, revenue share e fórmula líquida usada.
- Campanhas e linhas visíveis devem ter contagem reconciliada; não declarar totais que divergem da enumeração.

## Discord

- Usar bloco `text` com colunas alinhadas para consolidação desktop.
- Para operação que exigir visualização móvel, acrescentar cards verticais responsivos sem eliminar a tabela consolidada.
- Um bloco de tabela cercado por code fence é uma unidade visual atômica: nunca dividir suas linhas entre mensagens.
- Se o limite duro do Discord exigir múltiplas partes, cada parte com linhas de campanha repete título, cabeçalho completo e divisor; nenhuma parte pode começar por linhas órfãs.
- O contrato da operação define os emojis obrigatórios. Placeholders indisponíveis preservam o sinal visual aprovado (`⚪ N/D` quando aplicável), nunca removem silenciosamente o emoji.
- Dividir mensagens por capacidade real do Discord sem cortar uma linha, campanha ou code fence no meio.
- Usar a thread fixa do tipo de relatório quando registrada no contrato.
- Wrapper que publica diretamente usa cron `deliver=local` e stdout vazio para evitar duplicidade.
- Erro visível deve ser curto e sanitizado; detalhes técnicos ficam no audit/REPORT-INFRA.

## Audit mínimo

```text
operation_id, account_id, account_alias, mode, period, timezone, currency,
source_readbacks, campaigns_considered, rows_reported, action_candidates,
writes_attempted, writes_confirmed, errors, created_at
```

Nunca salvar token, cookie, senha ou payload secreto.
