# Sistema financeiro próprio — homologação e gates

Autorização: Rodolfo, 1545900695545192479, thread 1545426987756298340.
Runtime/código: `/root/mgs-agent/apps/finance-system/`. Procedimentos e lacunas: `README.md`. Estado vivo sempre no checkpoint `ZEUS-FINANCE-DASH-AUGUST-20260904`, não neste registro histórico.

## Procedimento reutilizável

1. Não usar resultados efetivos de fórmulas como entradas de um motor supostamente independente. Somente valores originais, cotações congeladas e fronteiras históricas explicitamente classificadas podem alimentar o cálculo. Recalcular recursivamente os precedentes e spreads; IFERROR não pode ocultar função não implementada, dependência ausente ou ciclo.
2. Preservar a diferença entre célula física vazia e fórmula que produz texto vazio. Referência direta à segunda deve manter vazio; transformar ambos em zero produz falsas divergências e altera guardas IF.
3. Dados descritivos do BASE_DASH exigem associação por binding de origem, não por índice de linha. SITE e PAÍS estão intercalados. Igualdade de totais não detecta dono/parceiro ligado ao segmento errado.
4. Separar gates: recálculo completo de fórmulas; primitivas financeiras nativas; fluxo de alterações; interface; produção. Um grafo de compatibilidade aprovado não equivale a CRUD completo, regras temporais, rollover e migração operacional concluídos.
5. Novos lançamentos de gestor devem propagar ao total/projeção, comissão com piso/faixas, pessoal e caixa. Não congelar a folha enquanto só se altera o lucro de mídia. Gestor não mapeado exige bloqueio ou opção SEM_COMISSAO explícita, nunca salário omitido silenciosamente.
6. Reconciliar todos os valores com tolerância documentada e acrescentar comparação de centavos. Diferenças residuais de Decimal/float muito abaixo do centavo não devem ser confundidas com erro financeiro; não arredondar intermediários arbitrariamente.
7. Testar importação idempotente, edição/retorno, revisão concorrente, baseline imutável, freeze, reabertura do banco e restore real. Dados sintéticos somente em cenários/DBs de teste identificados, nunca na referência MGS.
8. Homologação sem login produtivo fica privada. Em servidor compartilhado com sites, 127.0.0.1 sozinho NÃO isola outros usuários/processos do host: usar namespace de rede privado ou socket Unix com permissões restritas, além de diretórios privados e bloqueio público. Validar Host/Origin e private/ inacessível. Em Node fetch, o header Host pode ser ignorado pelo cliente; provar o teste com node:http para enviar o header real antes de classificar a proteção como falha.
9. Moedas renderizadas por Intl podem conter espaços não separáveis. Em telas estreitas, cartões em duas colunas podem transbordar mesmo com minmax(0,1fr); inspecionar scrollWidth/clientWidth e usar coluna única em phones, sem esconder o problema com overflow global.
10. Antes de encerrar o marco, nova leitura SA canônica de todas as fontes, comparação fórmula/valor, hashes, inventário e REPORT-INFRA. Não expor USUARIOS BOT, banco privado ou credenciais. Não declarar equivalência funcional integral enquanto qualquer gate de cobertura estiver pendente.

## Hospedagem protegida RunCloud

A configuração autorizada na mensagem `1545928620462313645` está documentada em `/root/mgs-agent/apps/finance-system/deploy/README.md`. Consultar esse runbook antes de operar `dash.mgsdigitalcorp.com` no MatteiInc01. Health exige namespace privado; HTTP 503 público é gate deliberado, não incidente. PostgreSQL produtivo e login ainda exigem seus gates; Supabase é opcional e não contratado. Não abrir acesso apenas removendo a proteção Nginx.

## Limites históricos da primeira homologação

Primeira versão implementou importação e recálculo integral de agosto/caixa/gestores, primitivas nativas principais, nove telas e cenários. Cadastro versionado completo, vigência/inativação, abertura de novos períodos, restante dos fluxos nativos e publicação/autenticação produtiva permaneceram abertos. O escopo integral autorizado não foi reduzido. Consultar o checkpoint para verificar se esses limites já foram superados.
