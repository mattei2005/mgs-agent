# SHEIN + CPV — 19/10/2026

Solicitante Rodolfo Mattei, thread1561388893558014103. Coleta read-only em 2026-10-20T07:42:00.748760-04:00, moedaUSD. Receita NET_REVENUE Smart Bidding apos revenue share e gasto por campanha Meta. ROI0-15 inclusivo, negativasROI<0. Conjuntos somados por conta+campaign_id antes da classificacao. Sem SMS/BOT, receitas sem gasto/identidade fora das faixas. Lucro de aquisicao antes dos demais custos operacionais. Mesmo contrato de dia civil no fuso de cada conta; payload SB19/10T03:00Z–20/10T02:59:59.999Z, todas779linhas comDATE19/10.

## Resultado

{
  "SHEIN": {
    "0_a_15": {
      "spend": "2933.56",
      "sb_spend": "2929.11",
      "net": "3188.85",
      "profit": "255.29",
      "count": 75,
      "roi": "8.702395723966784384842989405"
    },
    "negativo": {
      "spend": "2314.72",
      "sb_spend": "2310.41",
      "net": "1767.60",
      "profit": "-547.12",
      "count": 116,
      "roi": "-23.63655215317619409691020944"
    },
    "acima_15": {
      "spend": "23505.08",
      "sb_spend": "23465.71",
      "net": "35889.57",
      "profit": "12384.49",
      "count": 427,
      "roi": "52.68856774790811177839003313"
    },
    "total": {
      "spend": "28753.36",
      "sb_spend": "28705.23",
      "net": "40846.02",
      "profit": "12092.66",
      "count": 618,
      "roi": "42.05651096080597189337176594"
    }
  },
  "CPV": {
    "0_a_15": {
      "spend": "1099.63",
      "sb_spend": "1097.33",
      "net": "1202.40",
      "profit": "102.77",
      "count": 28,
      "roi": "9.345870883842747105844693215"
    },
    "negativo": {
      "spend": "279.18",
      "sb_spend": "278.03",
      "net": "259.24",
      "profit": "-19.94",
      "count": 10,
      "roi": "-7.142345440217780643312558206"
    },
    "acima_15": {
      "spend": "2828.30",
      "sb_spend": "2820.36",
      "net": "3622.08",
      "profit": "793.78",
      "count": 33,
      "roi": "28.06562245872078633808294735"
    },
    "total": {
      "spend": "4207.11",
      "sb_spend": "4195.72",
      "net": "5083.72",
      "profit": "876.61",
      "count": 71,
      "roi": "20.83639362888063302361953930"
    }
  },
  "TOTAL": {
    "0_a_15": {
      "spend": "4033.19",
      "sb_spend": "4026.44",
      "net": "4391.25",
      "profit": "358.06",
      "count": 103,
      "roi": "8.877836154507970117946340242"
    },
    "negativo": {
      "spend": "2593.90",
      "sb_spend": "2588.44",
      "net": "2026.84",
      "profit": "-567.06",
      "count": 126,
      "roi": "-21.86128994949689656501792667"
    },
    "acima_15": {
      "spend": "26333.38",
      "sb_spend": "26286.07",
      "net": "39511.65",
      "profit": "13178.27",
      "count": 460,
      "roi": "50.04397460561462296142766329"
    },
    "total": {
      "spend": "32960.47",
      "sb_spend": "32900.95",
      "net": "45929.74",
      "profit": "12969.27",
      "count": 689,
      "roi": "39.34795225917591587741315582"
    }
  }
}

Duas faixas pedidas: investimento6627.09; resultado-209.00. Acima15:460campanhas, investimento26333.38 e lucro13178.27. Consolidado campanhas689, gasto32960.47, receita45929.74, lucro12969.27, ROI39.35%.

## Validacao e ressalva

52identidades de contas validadas porAPI,30com gasto,689campanhas unicas com gasto(618SHEIN,71CPV),779linhas SB unicas. Cobertura SB×Meta integral para investimento positivo. Duas consultas SB estaveis. Sete testes de fronteira e conservacao decimal por grupo/faixa aprovados. 51das52contas fecham exatamente campanha=conta; conta2429758060563333 permanece com campanha5355.55 versus conta5355.40, diferenca0.15 apos repeticao scoped. Somatorio contas32960.32; somatorio campanhas32960.47. Nao afirmar conciliacao exata global, nao ratear0.15. Dois ultimos readbacks dessa conta preservam o residual. Outros pequenos ajustes historicos durante coleta reconciliados; snapshots Meta globais nao foram estaveis. Valores das duas faixas solicitadas permaneceram iguais entre primeira e ultima analise; ajustes observados entraram nas campanhas acima15.

SB investimento32900.95; diferenca para campanhasMeta59.52, sem causa comprovada. Os investimentos/lucros/ROIs usam exclusivamente gasto por campanhaMeta. Status analise entregue com ressalva de conciliacao0.15; nao certificada igualdade integral de contas. Relatorios18/10 preservados, sem reutilizar resultados. Nenhum write emMeta/SB/Finance/Router.
