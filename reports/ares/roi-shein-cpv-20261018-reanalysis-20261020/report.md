# Reanálise SHEIN + CPV — 18/10/2026

Rodolfo Mattei; thread 1561388893558014103. Reconsulta em 2026-10-20T07:23:22.978487-04:00. Mesmo período civil do relatório anterior, não transferido para 19/10. USD. Receita NET_REVENUE Smart Bidding após revenue share; gasto Meta Insights por campanha, total de conta independente. Dia civil no timezone de cada conta, mesmas convenções de data SB do snapshot anterior. Sem SMS/BOT, receitas sem campanha ou sem gasto não entram nas faixas. Lucro de aquisição, não P&L operacional completo.

## Resultado atual

{
  "SHEIN": {
    "0_a_15": {
      "spend": "5908.70",
      "sb_spend": "5908.45",
      "net": "6373.12",
      "profit": "464.42",
      "count": 114,
      "roi": "7.859935349569279198470052634"
    },
    "negativo": {
      "spend": "6394.13",
      "sb_spend": "6393.96",
      "net": "5338.61",
      "profit": "-1055.52",
      "count": 177,
      "roi": "-16.50764060161429310946133407"
    },
    "acima_15": {
      "spend": "19874.32",
      "sb_spend": "19874.03",
      "net": "27835.98",
      "profit": "7961.66",
      "count": 321,
      "roi": "40.06003727423126929625768328"
    },
    "total": {
      "spend": "32177.15",
      "sb_spend": "32176.44",
      "net": "39547.71",
      "profit": "7370.56",
      "count": 612,
      "roi": "22.90619274858090290780880221"
    }
  },
  "CPV": {
    "0_a_15": {
      "spend": "1184.73",
      "sb_spend": "1184.72",
      "net": "1282.02",
      "profit": "97.29",
      "count": 32,
      "roi": "8.211997670355270821199767036"
    },
    "negativo": {
      "spend": "158.82",
      "sb_spend": "158.82",
      "net": "142.11",
      "profit": "-16.71",
      "count": 5,
      "roi": "-10.52134491877597279939554212"
    },
    "acima_15": {
      "spend": "3248.51",
      "sb_spend": "3248.47",
      "net": "4337.74",
      "profit": "1089.23",
      "count": 36,
      "roi": "33.53014151103121123222646690"
    },
    "total": {
      "spend": "4592.06",
      "sb_spend": "4592.01",
      "net": "5761.87",
      "profit": "1169.81",
      "count": 73,
      "roi": "25.47462358941303031754811566"
    }
  },
  "TOTAL": {
    "0_a_15": {
      "spend": "7093.43",
      "sb_spend": "7093.17",
      "net": "7655.14",
      "profit": "561.71",
      "count": 146,
      "roi": "7.918736069856190869579314944"
    },
    "negativo": {
      "spend": "6552.95",
      "sb_spend": "6552.78",
      "net": "5480.72",
      "profit": "-1072.23",
      "count": 182,
      "roi": "-16.36255426945116321656658452"
    },
    "acima_15": {
      "spend": "23122.83",
      "sb_spend": "23122.50",
      "net": "32173.72",
      "profit": "9050.89",
      "count": 357,
      "roi": "39.14265684606944738165700306"
    },
    "total": {
      "spend": "36769.21",
      "sb_spend": "36768.45",
      "net": "45309.58",
      "profit": "8540.37",
      "count": 685,
      "roi": "23.22696081857619459324799200"
    }
  }
}

Soma das faixas solicitadas: investimento USD 13646.38; resultado USD -510.52.

## Comparação com relatório anterior

O gasto Meta passou de USD 36683.12 para USD 36769.21; diferença USD 86.09. Receita líquida total das campanhas com gasto permanece USD 45309.58. 4 campanhas mudaram de faixa após recálculo com gasto/receita atuais. Não inferir causa de ajustes históricos somente por estes números. Faixa0-15: antes144/6913.05/543.72; agora146/7093.43/561.71. Negativas: antes181/6480.20/-1058.19; agora182/6552.95/-1072.23.

## Validações

52 contas com identidade, nome, USD e timezone confirmados pela API; 30 com gasto. 785 linhas SB únicas; 685 campanhas Meta únicas com gasto, 612 SHEIN e73CPV; cobertura integral em ambos sentidos para investimento positivo; todos os conjuntos agregados antes da classificação. Soma campanhas=conta exata nas52contas, repetida em leitura independente. SB e Meta estáveis nas duas consultas desta reanálise; nenhuma paginação pendente. Limites0 e15 inclusivos, negativas estritamente<0; sete testes de fronteira/zero-spend aprovados e conservação decimal por faixa, operação e global.

Gasto Meta36769.21; SB36768.45; delta0.76. Não declarar igualdade dash×Meta, usar Meta em todo investimento/ROI/lucro. Diferença anterior66.49 não persiste no mesmo valor. Não inferir defasagem técnica ou causa não comprovada. Preservado relatório anterior; este é snapshot posterior do mesmo dia. Zero writes em Meta, Smart Bidding, Finance ou Router.
