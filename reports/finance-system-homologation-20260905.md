# MGS Finance — marco de homologação local

Autorização: mensagem Rodolfo `1545900695545192479`, thread `1545426987756298340`.
Código: `/root/mgs-agent/apps/finance-system/`.
Evidência estruturada: `private/final-evidence.json` dentro da aplicação.

## Resultado verificado

Aplicação web real, em execução somente em `127.0.0.1:8765`, banco PostgreSQL embarcado/PGlite persistente, Python Decimal e Node/Express. Health retornou `ok:true`, `mode:local-homologation`, `production:false`. Não houve publicação pública, instalação de serviço de sistema, autenticação nova, contratação/billing, alteração de credencial ou escrita Google.

- Importados 85.462 registros das nove abas financeiras, mais 406 precedentes históricos = 85.868 registros rastreáveis.
- 53.101 fórmulas inventariadas: 53.091 recalculadas com paridade; 10 cotações externas explicitamente congeladas.
- 75.517 comparações de resultados calculados/spills aprovadas, sem divergências na tolerância definida.
- 63.898 comparações numéricas, zero diferença no arredondamento a centavos; maior resíduo bruto numérico: 5.18428962420E-10.
- 43 segmentos, 78 combinações segmento-país, 2.418 registros diários normalizados.
- 19.344 verificações diárias por regras financeiras nativas, 9 verificações do caixa e 58 de despesas/pessoal: zero falhas.
- Caixa: lucro USD 35.799,80; 50% USD 17.899,90; 50% BRL 90.840,88. Câmbio e mês permanecem PROVISÓRIOS.
- Leitura final via Service Account nas seis planilhas: zero mudanças de fórmulas e zero mudanças de valores contra a captura auditada.

## Funcionalidades efetivamente exercitadas

Nove telas: visão geral, Caixa, sites/países, diário, gestores/comissões, despesas/pessoal, entradas/regras, reconciliação e histórico. Browser real Chromium: navegação, filtros, criação de cenário, edição de taxa, recálculo, readback de audit e retorno ao baseline. Zero erros JS. Sem overflow horizontal na visão geral a 390px.

15 testes Python aprovados; suíte integrada Node aprovada, incluindo importação idempotente, baseline imutável, edição/retorno de taxa, criação de lançamento nativo, revisão concorrente, cenário congelado, Host/Origin, private/ inacessível, banco reaberto e restauração de dump. Novo lançamento para gestor mapeado propaga a comissão/pessoal/caixa, testado. `npm audit --omit=dev`: zero vulnerabilidades reportadas.

## Escopo integral ainda aberto — não é conclusão do produto

A meta autorizada continua sendo toda a operação financeira. A primeira homologação não conclui:

1. Cadastros completos por vigência, inativação, contratos e abertura de novos períodos.
2. Conversão restante dos fluxos do grafo de fórmulas para operação nativa sem coordenadas; entrada ampla e importadores de relatórios.
3. Fechamento/liquidação produtivos, conciliação externa e regras de acesso empresarial.
4. Domínio/TLS, autenticação, PostgreSQL de produção, backup externo, observabilidade e cutover.

A tabela de versões no schema não é funcionalidade pronta. A grade histórica do Caixa não ganha células para lançamentos nativos; o consolidado nativo mostra esses deltas separadamente. Não usar a igualdade do total nem o PASS de fórmulas como justificativa para afirmar que tudo está concluído. Não houve exclusão de escopo aprovada.

## Falhas recuperadas durante construção

- Ausência de `python`: usado `python3`. Referência institucional fora do pack Hermes: localizada e lida no pack correto. Helper shell invocado inicialmente com interpretador errado; execução correta via bash validada.
- Primeiro recálculo confundiu resultado vazio de fórmula com zero em referências. Distinção corrigida; paridade integral reexecutada sem diferenças.
- Metadados por ordem de linha não refletiam SITE/PAÍS intercalados. Associação passou a usar a referência financeira exata; teste de parceiro/site validado.
- Teste Host em Node fetch não enviava a substituição esperada; node:http provou rejeição HTTP 403 real.
- Duas execuções browser detectaram overflow em moeda com espaços não separáveis. Diagnóstico scrollWidth/clientWidth identificou cartões; layout estreito corrigido e teste repetido passou.
- Teste de delta Decimal exigia igualdade além da precisão de 28 dígitos; teste passou a exigir 18 casas de diferença (muito menor que centavo), sem alterar a matemática ou tolerância de reconciliação monetária.
- Bloqueio falso do guard de gateway em uma leitura foi contornado com leitura direta Python; nenhum restart de gateway foi executado.

## Preservação e governança

Dados privados, banco, dumps, snapshots e node_modules excluídos do Git. Backups locais de teste foram restaurados em instância isolada; isso não é backup externo de produção. Diretórios e cenários de teste permanecem identificados, sem exclusão não autorizada. Código/arquitetura e procedimento institucional registrados; habilidade financeira atualizada para 0.1.15.
