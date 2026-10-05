# Auditoria técnica integral da dashboard financeira

Autoridade: Rodolfo Mattei, mensagem1556488447152099339, thread1545426987756298340. Coleta iniciada2026-10-05 02:12UTC. Escopo: diagnóstico técnico, performance, armazenamento, PostgreSQL, código, segurança, rotinas e recuperação. Não autoriza exclusões, alterações de regras ou novas escritas financeiras.

## Veredito

Auditoria concluída com achado funcional alto e melhorias propostas. Não é um atestado de sistema totalmente verde. A capacidade do servidor não é o gargalo principal; a aplicação transfere e processa documentos grandes, e o ambiente de desenvolvimento acumula artefatos. Não executar compactação destrutiva do PostgreSQL ou apagar backups por inferência.

Nenhum arquivo/banco foi excluído, nenhuma configuração produtiva/credencial/regra foi alterada e nenhum restart ocorreu. As escritas produtivas provocadas pelo auditor limitaram-se à autenticação/MFA/encerramento da sessão de validação. Navegador bloqueou todos os métodos mutantes financeiros. Foram criados evidências privadas, saídas de testes, relatório, checkpoint, inventário/audit e aprendizado na skill.

## 1. Achado prioritário: Nicolas/outubro retorna500

-44 verificações desktop/mobile cobrem Dashboard, Diário, Domínios, Contas, Despesas Gerais, Funcionários, Câmbio, Pagamentos, Atividades, Aprovações, Usuários, Perfil, Conferência e os cinco gestores; meses adicionais julho, agosto, setembro e dezembro2027.42 concluíram;2 falharam exclusivamente na visão Nicolas/outubro, uma por viewport. Zero erros JavaScript e zero POST financeiro. As duas respostas500 são falha real, não falha da ferramenta.
-85 combinações de17 workspaces×5gestores executadas com o módulo efetivamente implantado e conexão PostgreSQL read-only:84 passaram, Nicolas2026-10 falhou por `Manager current block total mismatch: Nicolas`.
-Causa isolada no snapshot outubro/revisão138: Eggbev, conta1001115192056600, dois `account_spend` novos deUSD141.29 em02/10 eUSD146.83 em03/10, totalUSD288.12. Os gastos entram nas células diárias por país, mas os agregados legados usados no total do gestor não os acompanham.
-Exemplo do snapshot:02/10 detalheUS−4207.91 versusTOTAL−4066.62;03/10−4235.34 versus−4088.51. Diferenças−141.29 e−146.83. `managerView` soma os detalhes e bloqueia corretamente a discrepância de−288.12; o total persistido do gestor é7138.09161542732019551188751, enquanto os blocos somam6849.971615427322 no mesmo câmbio/revisão. Valores provisórios, não proposta de pagamento.
-Reprodução offline do motor com entradas/as_of exatos reproduziu integralmente os documentos persistidos de setembro e outubro: a divergência não é cache velho e não desaparece com simples recálculo do código atual.
-A correção exige alinhar a propagação de gastos nativos e agregados do gestor; pode afetar base/comissão. Não esconder o erro, não apagar gastos, não reduzir totais arbitrariamente, não aumentar tolerância. Nenhuma correção financeira publicada. Autorização específica pendente.
-A versão diagnóstica privada de `manager-view` apenas expôs o delta; seu campo interno herdado `pass:true` não é aceitação. O verificador produtivo original permaneceu intacto e registrou FAIL.

## 2. Performance medida

Medições do VPS via HTTPS real; amostra curta, não SLA nem teste sustentado de usuários reais.

-Workspace outubro:6,228,606bytes descomprimidos;miss947.76ms, hits501.78–670.19ms. Tempo interno miss414ms;hits114–151ms. Payload de modelo4,402,319bytes, domínio1,617,344bytes.
-Workspace setembro:10,159,330bytes descomprimidos;miss1083.85ms, hits690.93–790.42ms. Modelo6,192,774bytes;adições1,325,121bytes.
-Histórico julho:10,149,046bytes;581.72–612.64ms.
-Gestor Ícaro/outubro:48,021bytes;254.18–300.13ms, mostrando a vantagem do endpoint especializado.
-20 requisições simultâneas ao workspace outubro:20HTTP200, mediana3088.55ms, p953499.86ms, máximo3502.03ms.
-Gzip ativo. Esses tamanhos não equivalem ao tráfego comprimido. No navegador, uma amostra outubro desktop transferiu274,844bytes no conjunto de recursos medidos, contra6,957,494bytes descomprimidos.
-42 verificações renderizadas: maior tempo medido2051ms (julho/mobile); sem overflow global. Não incluir os dois timeouts do Nicolas como se fossem latência normal.
-Cache hit/miss preservou SHA-256 exato do payload de cada competência na série sequencial.
-Plano PostgreSQL porPK:0.060ms metadados/0.058ms SELECT*. Audit por cenário0.420ms;primeira página de source_cells0.484ms. Esses tempos não incluem descompressão/transferência/parse da aplicação.
-Leitura real do cenário outubro via driverNode no host produtivo:89.94–122.91ms em5amostras.
-Motor Python local:13.838s outubro e13.947s setembro, resultado integral idêntico ao snapshot. Não é benchmark de salvar em produção nem comparação de hardware.

### Melhorias recomendadas

1.Resolver o cache por metadados/revisão antes de buscar/decodificar o cenário e cadastro completos. Hoje `scenario()` e `accountDocument()` precedem o teste de cache em workspace.mjs. Preservar chaves de revisão/câmbio e isolamento.
2.Entregar dados por tela e carregar detalhes/editor sob demanda. O modelo completo não é necessário para cada resumo. Planejar endpoints versionados com paridade integral e fallback, não simplesmente remover campos.
3.Perfilar o recálculo para reduzir trabalho de reconstrução do grafo. Manter Decimal, validações e resposta somente após commit. Não cachear resultado financeiro sem invalidação correta.
4.Adicionar métricas de latência/payload/erros por rota e checks de todos os gestores/competências correntes. Green unit tests e health200 não detectaram o500 específico.

## 3. Banco de dados e compactação

-Banco produtivo439,875,263bytes (419.50MiB),349cenários,85,868source_cells,40documentos históricos,28lançamentos de ledger.14tabelas públicas examinadas com colunas, índices, constraints, grants e triggers.
-Scenarios ocupa363,118,592bytes (346.30MiB) incluindoTOAST/índices. Results comprimidos somam325,162,603bytes, contra2,524,304,250bytes deJSON lógico: redução de87.12% já existente.348resultados usamPGLZ;um pequeno documento não precisa de compressão.
-219snapshots de recuperação locked somam279,354,433bytes:85.91% do espaço comprimido de results.17workspaces ativos somam20,524,673bytes. Histórico/recovery não é lixo.
-109outros cenáriosdraft precisam de classificação individual se vier a existir política de retenção; nome/state sozinho não prova inutilidade.
-Índices examinados válidos. Zero deadlocks nas estatísticas. Sem evidência de necessidade imediata de novos índices ouVACUUM FULL.
- Autovacuum ligado. Embora a tabela pai scenarios mostre zero autovacuums nesse ciclo estatístico, seu TOAST tem 107 execuções e última observada em 2026-10-05T01:58:32.728745Z. Não confundir estatísticas da tabela pai com ausência de manutenção dos documentos grandes.
-Estatísticas acumuladas de algumas tabelas mostravamn_live_tup=0 apesar de dados existentes; count(*) e catálogo confirmaram85,868source_cells. Não são tabelas vazias.
-pg_stat_statements ausente, track_io_timing off e logging de queries lentas desativado. Melhorar observabilidade antes de parametrização ampla; respeitar privacidade dos parâmetros e gates de configuração.
-533sessões no corte pós-login:7ativas/526inativas. Tabela≈240KiB. Purga de sessão tem benefício de higiene, não ganho material de disco; exige política que preserve login persistente/revogação/audit.
-LZ4 pode ser ensaiado como trade-off CPU/espaço, mas não foi medido; nenhuma porcentagem adicional prometida. Não recomprimir ou reescrever banco produtivo durante auditoria.

## 4. Arquivos e bancos auxiliares

Separar host Zeus, host RunCloud e banco ativo:

-Árvore local finance-system antes dos novos testes:49,537,228,800bytes alocados (46.14GiB);discoZeus70% ocupado.
-Maior família local:gam-email-runs7,747,706,880bytes.61dumps maiores que10MiB nessa família somam7,444,951,040bytes; não foram classificados como redundantes.
-Árvore queue-four≈5.7GB e várias árvores de preparação/teste entre1–3GB. São ocupação medida, não espaço já liberável.
-No PostgreSQL remoto existem48bancos auxiliares financeiros de testes/restauração,8,727,769,024bytes (8.13GiB), além do banco produtivo. Inventário completo emdeep-db.json. NenhumDROP, start de banco antigo, exclusão ou retenção nova executados.
-Dumps remotos em/home/zeus/mgs-finance-backups:11,314,839,552bytes;backups de/home/mgsfinance:512,225,280bytes. Não somar isso aos dados produtivos como se tudo fosse banco ativo.
-RunCloud14% de disco ocupado;aplicação≈347MB de memória ePostgreSQL≈783MB, ambos comlimite3GiB;serviços ativos. Sem indicação de necessidade de aumentar servidor.
-A revisão anterior dos18diretórios permanece válida:todos preservados,10.63GiB,zero candidatos com descarte seguro comprovado. Esta auditoria não supersede a preservação.
-Os testes desta própria auditoria criaram4novos artefatos de banco/dump totalizando869,543,936bytes (829.26MiB), enumerados emaudit-storage.json. Estão retidos e são responsabilidade deste trabalho; não afirmar que a auditoria não escreveu arquivos.

Recomendação: política manual por classe, preservando fontes, fixtures, histórico, evidências referenciadas e último rollback válido; reconstrução testada e manifesto exato antes da confirmação destrutiva. Não criar cron de limpeza e não pedir exclusão de um volume genérico.

## 5. Segurança, rotinas e recuperação

-Login público200; navegação protegida303/login, APIs/arquivos protegidos401 sem sessão; caminhos sensíveis404 autenticado. MFA owner real validado;7identidades comMFA active no banco. Não foram feitos novos logins reais dos outros6usuários.
-CookieSecure/HttpOnly/SameSiteStrict;HSTS/CSP/Permissions-Policy/noindex presentes. Origem direta403 eCloudflare200 sem credenciais nos probes.
-PostgreSQL somente socket, rolemgsfinance semsuperuser/createdb/createrole/replication. Grants/triggers de proteção examinados sem alteração.
-113caminhos locais comparados;94existem também no remoto,93hashes idênticos. Diferença package.json é o script localtest:release, com dependências idênticas;19caminhos são ferramentas locais não implantadas. Nenhum drift de código compartilhado executável detectado.
-GAM e gastos até03/10 statusok/failure_streak0;SMS até03/10 registrado;cutoffoutubro03/10 coerente com o momento da auditoria. Isto não substitui reconciliação externa de todas as fontes.
-Estado de backupfull04/10PASS, componentePostgreSQL224,141,580bytes. Último restore04/10 10:23UTC PASS:6componentes,infra17membros,knowledgePASS e catálogoPGPASS. `finance_postgresql_materialized:null`: esse teste semanal NÃO materializouPostgreSQL. Recomenda-se drill periódico materializado em ambiente realmente isolado; não declararrestorecompleto do banco por catálogo apenas.
-Nenhum erro de prioridadeerr nos journals dos dois serviços na janela observada. Não significa ausência de erroHTTP: o casoNicolas confirma lacuna na observabilidade.

## 6. Validação, incidentes da coleta e limites

-249Node+203Python=452testes pass,zero skips. GatePython inicial foi interrompido pelo teto400s da ferramenta; repetido integralmente em processo silencioso,565.67s,PASS,resultado consumido e processo encerrado antes da entrega.
-Uma redução do relatório offline acessou counts['error'] ausente e retornouKeyError; o cálculo havia terminado. Diagnóstico corrigido para registrar o mapa real de counts e os dois recálculos foram repetidos, ambos com paridade integral. Ausência de categoria não foi tratada como valor financeirozero.
-Skill audit:39Markdown,zero referências/evidências faltantes. Aprendizado de auditoria inclui cacheantesdeJSON,TOAST,artefatos próprios e integrações de gastos×agregados de gestores.
-417registros comparados por fingerprint (349cenários+28ledger+40históricos). Mudaram somente workspacessetembro/outubro:revisões998→999 e137→139;adições nominais idênticas,demais415registros idênticos. Eventos financeiros3022/3023(cotaçãoautomática) e3026(actorrodolfo,atualização de cotações) reconciliam a mudança; não atribuir essas revisões ao auditor nem declarar banco inteiro imóvel.
-O código implantado original passou84/85reconciliações de gestor;Nicolas continuaFAIL. Nenhuma recuperação funcional foi declarada.
-Não houve pentest externo destrutivo, teste de carga sustentado, DMLfinanceiro, mudança de esquema,VACUUM,REINDEX,compressão,limpeza,publicação ou resetdeautenticação. Não houve nova conciliação de todas as planilhas/receitas de todos os meses. Escopo é auditoria técnica do sistema, com amostras e cobertura explicitadas.

## Ordem operacional proposta

1.Corrigir propagação de gastosEggbev/Nicolas/outubro com fonte/revisão congelada,ensaio,backup,recálculo e impacto exato na remuneração;aprovaçãofinanceira separada.
2.Otimizar leituras/cache e carga por tela com paridade e canário;monitorar latência/erros e adicionar cobertura do caso vivo.
3.Classificar arquivos/bancosauxiliares por retenção e recuperabilidade;somente depois apresentar lista exata para confirmação de descarte.
4.Ampliar observabilidadePG e periodicidade de restore materializado;testar compactação apenas se houver benefício demonstrado.

Evidências privadas:apps/finance-system/private/audit-1556488447152099339/. Não anexar nem publicar snapshots financeiros ou credenciais. Próximas alterações dependem do escopo aprovado, com gatesCríticos separados.
