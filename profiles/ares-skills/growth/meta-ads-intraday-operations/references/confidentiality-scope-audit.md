# Auditoria de confidencialidade e escopo — procedimento

Fonte de autoridade: `/root/mgs-agent/context/ares-asset-scope.md` e cadastro positivo `data/ares/asset-scope.json`. Este procedimento verifica a implementação; não amplia escopo nem autoriza mudar credenciais, permissões ou isolamento.

1. Separe política, cobertura do transporte e isolamento efetivo. Cadastro válido e testes verdes do gate não demonstram confidencialidade de todas as rotas.
2. Inventarie o profile ativo e fontes operacionais compartilhadas, incluindo arquivos ocultos, mirrors, caches, backups, arquivos compactados e bancos SQLite. Deduplicate por inode e registre explicitamente exclusões, symlinks quebrados, mídia apenas inventariada e bancos ilegíveis. Não inspecione fontes privadas de outro agente como atalho para relatórios.
3. Busque identificadores privados somente em processamento local; emita categorias, contagens e identificadores opacos, nunca linhas correspondentes ou hosts bloqueados. Não copie os dados privados encontrados para o contexto, relatório, skill ou evidência compartilhada.
4. Em SQLite, consulte em modo read-only. Conte mensagens canônicas separadamente dos mesmos registros nos índices FTS. Distinga contexto fornecido pelo usuário de retorno de ferramenta ou relatório; um histórico limpo pode ser recontaminado pelo contexto de um canal compartilhado.
5. Execute a suíte existente e acrescente provas offline com IDs sintéticos: `act_<id>/edge`, nó numérico sem prefixo, `me/adaccounts`, `me/businesses`, business/owned_ad_accounts, objeto filho sem proveniência, campos account_id e batches com identificadores em query/body. Nenhum teste negativo pode fazer HTTP com ativos reais fora do cadastro. Preserve separadamente a exceção técnica do app autorizado.
6. Verifique transportes diretos e helpers alternativos. Importar o helper central não prova que todos os requests passam pelo gate; procure chamadas diretas e valide a proveniência de objetos filhos e sua conta antes do request. No helper atual, um ID numérico de campanha/conjunto/anúncio só pode ser lido após descoberta por edge de conta aprovada, registrada pelo próprio transporte em `scoped-object-provenance.json`; declarar `account_id` no parâmetro não comprova ownership. Em retomadas frias, fazer primeiro a leitura account-scoped necessária, sem consultar o ID desconhecido para tentar descobrir sua conta.
7. No helper Smart Bidding, use respostas sintéticas e transporte mockado para testar seleção de empresa/publisher e validação do host antes da consulta. Uma resposta global retornada sem restrição demonstra ausência de enforcement local, mas não prova sozinha qual é o alcance real da credencial no servidor. Não obtenha dados reais externos para provar a falha.
8. Confira o runtime: usuário do serviço, backend do terminal, restrições de filesystem e disponibilidade de fontes/credenciais compartilhadas. Um profile separado executando como root com terminal local não equivale a isolamento de arquivos ou rede.
9. Reconcilie limites da varredura antes de concluir. Para arquivos compactados, reporte membros separadamente de arquivos externos; para FTS, não some cópias como mensagens novas. Guarde progresso incremental e divida a varredura se houver timeout.
10. Entregue achados com grau de evidência e limite: proteção comprovada, falha reproduzida offline, risco não exercitado e cobertura não validada. Não transforme auditoria read-only em correção de segurança não autorizada. Atualize checkpoint com próxima ação exata e evidência redigida.

## Verificação mínima

- Suites do cadastro e do domínio passam, sem considerar isso prova E2E.
- Provas negativas não usam credenciais nem rede.
- Relatório e checkpoint não contêm identificadores privados ou amostras de payloads reais externos.
- App/permissões/campanhas permanecem intactos durante a auditoria.
