# Agosto: autorização recebida e gate dimensional

## Autoridade vigente

Rodolfo1551305457015062610, thread1545426987756298340, autorizou aplicar os valores da planilha/GAM aos itensAV, M2 e22sites divergentes. Confirmou gastos e informou ter corrigido manualmente os três subtotaisSB. Critério explícito: receitas por vertical e gestor devem reconciliar com o total de CADA domínio/subdomínio. São dimensões cruzadas dos mesmos fatos; nunca adicionar receita por gestor novamente à receita por vertical.

A autorização está recebida e não precisa ser repetida. Não houve aprovação para inventar atribuição, distribuir proporcionalmente, preservar automaticamente uma divisão antiga sem evidência nem usar país desconhecido para declarar o trabalho completo. O escopo integral permanece aberto, sem redução.

## Readback novo

Evidências privadas/ignoradas peloGit: `/root/mgs-agent/apps/finance-system/private/apply-1551305457015062610/`.

Todas as oito abas foram relidas viaSA canônica em FORMULA/UNFORMATTED_VALUE/FORMATTED_VALUE. Desde a reauditoria1551300167230029965, as únicas células com mudança de valor são as três correções manuais:

- rede1SB!F165 =SUM(E96:E165): CAD109.935,81.
- rede1SB!F276 =SUM(E194:E276): CAD3.638,02.
- rede1SB!G1877 =SUM(E1784:E1877): CAD26.981,23.

Os fatos financeiros da Sheet não mudaram; portanto, continuam válidos os totais e deltas da reauditoria. RevisionsSQL live: workspace2026-08=392, master-ad-accounts=7. Nenhuma escrita financeira nesta tarefa. Não foi feito backup completo/dump nem extraída autenticação.

## Por que total mensal não basta para aplicar com a aceitação exigida

SB fornece placement, país e medium. O detalhado AV atual só fornece Date, Site, campaign, term, content, medium e revenue. Não tem campo explícito de vertical/placement/país da operação; parte das linhas também não oferece tracking para cruzamento. M2 contém apenas data, domínio, campanha e gross. Classificar b01comoDireto e demaisBOT não cria por si só um país/vertical onde a operação é ambígua.

Contraprova concreta, fonte atual:

- AV detalhado, linha334: data01/08, domínioeggbev.com, campaign/term/content todos`-`, mediumg006-d, grossUSD21,65.
- O gestorG006/Nicolas e o domínio são conhecidos; a vertical operacional não está identificada nessa linha.
- Eggbev tem receitasUS eGB na própria fonteSB: CAD109.935,8090757732364564753 emUS eCAD182,2659696086575511 emGB. O nome do domínio ou o gestor sozinho não resolve qual vertical deve receber esse valorAV.
- Somente Eggbev possui35linhas positivas g006-d sem campaign/term/content, totalUSD406,19, além de uma g006-s deUSD1,71. Essa é uma evidência de perda dimensional, NÃO um total definitivo de todas as linhas não classificáveis; outras linhas ainda exigem mapas de campanha.

Foi consultado também históricoDTR/SB de campanhas. Há identidade histórica para pg19326(WantabrandGB) e pg19236, mas identificação de páginas específicas não resolve linhas sem campanha nem autoriza reaproveitar aliases históricos como regra para toda a receita. Não foi alterado nenhum mapaDTR/SB.

O detalhe original do GAM deve fornecer a vertical operacional, ou URL/placement/ad-unit que permita cruzá-la de forma inequívoca, mantendo domínio/subdomínio, data, medium/gestor e gross. País de geolocalização do visitante não equivale automaticamente a país/vertical da operação.

## Próximo passo autorizado e dependência

A aplicação integral AV/M2/22sites está autorizada e pendente de fonte/mapeamento dimensional suficiente. Os totais continuam sendo os da planilha, inclusive o consolidadoAV. Precisamos de complementoAdOps ou de uma regra explícita para a parcela verdadeiramente sem identificação; não solicitar novamente autorização genérica para corrigir a dash.

Não aplicar ajuste artificial em um dia nem ratear diferenças de fechamento por países/verticais para forçar soma. Fechamento deve provar `soma(fatos vertical×gestor)=gross de cada domínio/subdomínio`, sem dupla contagem e com fechamento mensal identificado.

PEND-092 permanece aberta; gastos e21sitesSB já conciliados são preservados. Nenhuma nova correção de receita foi declarada aplicada. Regra de aceitação salva na skill financeira `references/adops-monthly-source-reconciliation.md`; checkpoints e inventário são documentação/continuidade, não mudanças financeiras.
