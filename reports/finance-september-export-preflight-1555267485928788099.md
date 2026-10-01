# Setembro/2026 — análise dash → seis planilhas

Pedido de Rodolfo1555267485928788099, thread1545426987756298340: analisar a atualização da principal e Kelly/Isliago/George/Nicolas/Joe, apresentar antes de aplicar. **Autorização atual somente diagnóstico. Zero gravações financeiras no dashboard ou Google Sheets.**

## Fonte e comprovação

- Consulta SELECT READ ONLY ao PostgreSQL financeiro remoto, workspace-2026-09 revisão917, atualizado2026-10-01T16:57:19.082982+00:00. Cutoff30/09,30datas presentes. Cálculo de gestores reproduzido sobre essa mesma captura; hashes locais de manager-view.mjs, manager-layouts.json e periods.mjs iguais aos produtivos; cinco controles de soma por site PASS. Não houve login/UI nem execução de import financeiro nesta análise.
- Google Sheets/Drive GET via Service Account canônica: seis IDs/gids fornecidos resolvem exatamente Setembro2026 e todos canEdit. Abas completas capturadas com fórmulas, valores efetivos e formatados; nenhum erro de fórmula exibido.
- Evidência privada durável: apps/finance-system/private/september-export-preflight-1555267485928788099/. manifest.json contém hashes das seis capturas; analysis.json contém comparação, manager-runtime-code-verification.json a paridade de código, dash-scenario.json a fonte consistente. Nenhuma promessa de paridade pós-escrita: execução e ensaio ainda dependem de aprovação.

## Diagnóstico principal

A principal não está preenchida com setembro da dash: receitas diárias USD0.02 (AutoCreditAdx AKU13) e mídia0. Na dash: brutoUSD759172.5714620239551642007408; mídiaUSD522239.3752008700793661820715; despesas geraisUSD21170.57653586779930911683636; pessoalUSD14063.11317361294436030795499; lucroUSD88955.60787022513353303000281. A planilha exibe lucroUSD-14361.028498397278 por refletir despesas sem o movimento do mês.

O mês tem dias completos no sistema, mas taxas/câmbios continuam provisórios: não é prova de liquidação dos parceiros. Fonte dashUSD/BRL5.182056 e USD/CAD1.4250049999999999 nessa revisão. A planilha geral tinha5.174532/1.424920 na captura; a cotação continuou variando na releitura. Não fixar liquidação nem criar ajuste de receita para esconder diferença temporal de câmbio.

### Estrutura necessária

- Oito sites com receita na dash não possuem bloco próprio detectável nos cabeçalhos de receita da principal: Boostingecon, Cephyric, Escalatepower, Growpowerhub, Mavroa, WavesBee Finanzas, Zyclor e dicasfinancas.info.
- CreditoParaVeiculo e GameZoneAd têm receita BR no sistema mas cabeçalho US na planilha. Adequar classificação/bloco por país, sem descartar receita nem inventar geografia.
- Vizioid está INATIVO no campo de rateio da planilha e ATIVO na dash. Copiar a participação mensal vigente, não aplicar novo ownership global.
- Receitas nativas somadas em origem: CAD783034.41730848215352174241 e USD209553.70626105164338315381. Preservar pares de moedas e atribuição gestor/site/país/dia; não somar CAD ao USD já convertido nem replicar o site compartilhado inteiro em vários gestores.

### Gestores

Resultado USD e remuneração de gestor BRL da revisão917:
- Kelly16409.562214459467;5952.47. Falta Yolokfx no resumo atual.
- Isliago28867.60185396071;14959.35. Faltam WavesBee Finanzas e Yolokfx.
- George/Ícaro-778.655461622288;3000.00, piso mensal. Faltam Portal Relevante e Yolokfx.
- Nicolas52127.380584310595;27012.70. Faltam Yolokfx, Zuout e Zuout Finanzas.
- Joe9514.482700438708;3451.32. Faltam TopFeed e Yolokfx.

Kelly tem ainda BRL3000 de criação de criativos, rubrica separada; não está incluída nos5952.47 de gestora. Remuneração não é saldo a pagar: ledger/pagamentos/créditos não foram incluídos nesses números e não serão executados por inferência.

Nas cinco planilhas A1 ainda diz Agosto e H1 importa CAIXA SINTETICO!J2=5.11, agosto, em vez do câmbio de setembroK2. Corrigir essas referências no futuro lote aprovado. A principal já referencia as abas Setembro2026 na folha; não repetir diagnóstico antigo de folha apontando para agosto. Projeções de gestor são calendárias e, após30/09, igualam o acumulado; já a estimativa geral J139 mantém divisor6 e deve ser adequada ao mês completo.

73spills de dados,29053células comparadas integralmente;1302diferenças numéricas, todas em duas classes de delta (custo diário e seu subtotal), máximoUSD0.04514920360946917. Evidência consistente com cache/volatilidade do rateio, não prova de fórmula estrutural incorreta; validar novamente com base cambial comum e tempo de propagação antes de alterar IMPORTRANGE por esse motivo. Nenhuma diferença textual nesses spills. Cinco H1 dependem do Caixa agosto confirmado à parte.

### Despesas

Mudanças nominais company confirmadas, origem Sheet → dash:
- Google AI Fow USD150→224.98;
- Claude Console USD100.03→100;
- Honcho USD10→25;
- APP USD0→265;
- SMS Funnel BRL30000→95000;
- pushalert USD0→99;
- JBF Wire Fee CAD25→40.

Três despesas ativas novas sem linha legado: SB Wire Fee USD10; Elevenlabs USD11; voicemaker USD10. Arquivadas devem permanecer sem efeito, mesmo quando edit_amount conserva um valor antigo. Na folha fixa, Jislaine BRL1500 na planilha versus3000 na dash. As demais remunerações precisam recalcular com o resultado e piso/faixa corretos, incluindo arredondamento pagável em BRL. Não substituir fórmulas por constantes sem um desenho explícito.

## Caixa e escopo proposto

CAIXA SINTETICO setembro=K: cotação automática existe e fórmulas totais estão presentes, mas49linhas preenchidas no mês anterior estão vazias em setembro. Isso é necessidade de remapeamento pelas linhas reais de setembro, não autorização para copiar49células cegamente nem importar valores de agosto. Incluir somente a coluna de setembro, suas dependências confirmadas e a preservação dos demais meses na aprovação do lote.

Proposta: exportação única da dash para setembro nas seis abas, com adequação mínima de blocos/atribuições/câmbio/folha/despesas e CaixaK. Preservar estilos/fórmulas úteis; snapshot completo+hash antes; ensaio offline; mapa de células e verificação de todos os destinos; aplicar só após Rodolfo confirmar; reler integralmente diário, sites, gestores, remuneração e consolidado sob câmbio comum. Nada de alterar dashboard, meses anteriores, dados de outubro, pagamentos, créditos, acessos ou criar sincronização automática. Exceções ainda descobertas no ensaio bloqueiam a escrita correspondente, não autorizam esconder resíduos com ajustes.

## Próximo passo

Aguardar autorização explícita do escopo acima. Depois reler fonte viva e alvos, construir o mapeamento celular final e provar paridade antes da transação. Valores aqui são referência da captura, não taxas fixadas nem garantia do centavo de um instante futuro.
