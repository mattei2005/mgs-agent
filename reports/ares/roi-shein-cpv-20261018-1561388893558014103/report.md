# ROI SHEIN e CPV — 18/10/2026

Solicitante Rodolfo Mattei; thread 1561388893558014103. Consulta read-only concluída em 2026-10-19T08:40:27.013319-04:00. Valores USD. Sete publishers canônicos, domínios aceitos pelo gate. Escopo Meta: 36 contas SHEIN e 16 contas CPV, 30 com gasto no dia. 685 campanhas com gasto: 612 SHEIN e 73 CPV. Dia civil 18/10/2026 no fuso de cada conta; contas com gasto SHEIN America/New_York, CPV America/Sao_Paulo.

## Critério

Agregação de adgroups SB por conta + campaign_id antes da classificação. Receita = NET_REVENUE, revenue share já descontado. Lucro = NET_REVENUE SB − gasto real Meta. ROI = lucro/gasto Meta. Faixa 1: 0≤ROI≤15%; faixa 2: ROI<0. Nenhuma campanha exatamente no zero. Nenhuma campanha Meta com gasto sem correspondência SB e nenhuma SB com investimento sem correspondência Meta. SMS, BOT, receita sem campanha e receita sem gasto não atribuídos às faixas; trata-se de resultado de aquisição, não lucro contábil após todos os custos.

## Resultado final

{
  "SHEIN": {
    "0_a_15": {
      "spend": "5777.67",
      "sb_spend": "5768.55",
      "net": "6229.30",
      "profit": "451.63",
      "count": 113,
      "roi": "7.816818890660075774490408763"
    },
    "negativo": {
      "spend": "6321.49",
      "sb_spend": "6311.57",
      "net": "5279.90",
      "profit": "-1041.59",
      "count": 176,
      "roi": "-16.47696982831579263749527406"
    },
    "acima_15": {
      "spend": "19999.74",
      "sb_spend": "19964.62",
      "net": "28038.51",
      "profit": "8038.77",
      "count": 323,
      "roi": "40.19437252684284895703644147"
    },
    "total": {
      "spend": "32098.90",
      "sb_spend": "32044.74",
      "net": "39547.71",
      "profit": "7448.81",
      "count": 612,
      "roi": "23.20581079102399147634342610"
    }
  },
  "CPV": {
    "0_a_15": {
      "spend": "1135.38",
      "sb_spend": "1132.65",
      "net": "1227.47",
      "profit": "92.09",
      "count": 31,
      "roi": "8.110940830382779333791329775"
    },
    "negativo": {
      "spend": "158.71",
      "sb_spend": "158.33",
      "net": "142.11",
      "profit": "-16.60",
      "count": 5,
      "roi": "-10.45932833469850671035221473"
    },
    "acima_15": {
      "spend": "3290.13",
      "sb_spend": "3280.91",
      "net": "4392.29",
      "profit": "1102.16",
      "count": 37,
      "roi": "33.49898028345384528878798102"
    },
    "total": {
      "spend": "4584.22",
      "sb_spend": "4571.89",
      "net": "5761.87",
      "profit": "1177.65",
      "count": 73,
      "roi": "25.68921212332741447836273128"
    }
  },
  "TOTAL": {
    "0_a_15": {
      "spend": "6913.05",
      "sb_spend": "6901.20",
      "net": "7456.77",
      "profit": "543.72",
      "count": 144,
      "roi": "7.865124655542777789832273743"
    },
    "negativo": {
      "spend": "6480.20",
      "sb_spend": "6469.90",
      "net": "5422.01",
      "profit": "-1058.19",
      "count": 181,
      "roi": "-16.32958859294466220178389556"
    },
    "acima_15": {
      "spend": "23289.87",
      "sb_spend": "23245.53",
      "net": "32430.80",
      "profit": "9140.93",
      "count": 360,
      "roi": "39.24852307033057719944336314"
    },
    "total": {
      "spend": "36683.12",
      "sb_spend": "36616.63",
      "net": "45309.58",
      "profit": "8626.46",
      "count": 685,
      "roi": "23.51615675002562486506055101"
    }
  }
}

As duas faixas solicitadas somam investimento USD 13393.25 e resultado USD -514.47.

## Conciliação real

Gasto total Meta USD 36683.12; investimento SB USD 36616.63; diferença USD 66.49. SHEIN: Meta 32098.90 e SB 32044.74; CPV: Meta 4584.22 e SB 4571.89. Não afirmar igualdade SB×Meta. O relatório usa integralmente o gasto Meta para investimento/lucro/ROI.

Duas consultas SB, HTTP201, 785 linhas cada, valores e chaves idênticos, DATE exclusivamente 2026-10-18. Meta inicial: USD36682.46; leitura independente posterior e recuperação scoped: USD36683.12. Ajustes históricos observados USD0.66, preservados nos arquivos; snapshots Meta não foram estáveis. No snapshot final, soma de todas as campanhas coincide exatamente com Insights de conta nas 30 contas com gasto. 52 identidades vivas confirmadas; todas as 104 consultas iniciais Meta e os readbacks aprovados, sem paginação pendente. Novas consultas futuras podem conter novos ajustes de plataforma.

## Testes

Sete testes de limites/sem gasto, unicidade de 685campaign IDs por conta, cobertura integral Meta×SB, soma campanha=conta, conservação por faixa/estratégia/global e estabilidade do readback SB aprovados. Classificação usa precisão decimal integral. Skill paid-acquisition-operations/references/smartbidding-roi-band-reconciliation.md atualizada com procedimento geral de conciliação Meta e faixas personalizadas; patch lido de volta e testes aprovados. Sem writes em Meta, SB, Finance ou Router.
