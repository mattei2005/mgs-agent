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
9. Reconcilie limites da varredura antes de concluir. Inventarie todos os arquivos do recorte, mas leia texto, SQLite e compactados por mecanismos próprios; não desperdice a busca textual percorrendo integralmente mídia e grandes bancos binários. Grave progresso incremental desde o primeiro lote, não apenas depois de um timeout. Deduplicate arquivos por inode, reconcilie links quebrados e diferencie um banco parcialmente ilegível de um banco integralmente consultado. Conte membros de compactados separadamente dos arquivos externos e não some cópias FTS como mensagens novas.
10. Entregue achados com grau de evidência e limite: proteção comprovada, falha reproduzida offline, risco não exercitado e cobertura não validada. Não transforme auditoria read-only em correção de segurança não autorizada. Atualize checkpoint com próxima ação exata e evidência redigida.

## Correção autorizada e regressão

1. Congele a evidência anterior e enumere os caminhos exatos que serão alterados. Separe mudanças locais autorizadas das mudanças de execução/credenciais sujeitas ao gate próprio; não reclassifique um desenho de isolamento ainda não implantado como solução validada.
2. Antes de modificar um helper compartilhado, localize os consumidores, transportes diretos e testes que exercitam sua assinatura. Preserve contratos de retorno e o modo dos outros agentes; um import do helper não garante que chamadas de nível inferior estejam protegidas.
3. Teste seletores conflitantes em todos os níveis: path, query, body e batch. Inclua `ids` junto de um path já permitido, parâmetros duplicados e expansões de campos que façam descoberta. Não aceite `account_id` informado pelo chamador como prova de ownership de um objeto.
4. Separe catálogo de relatório. Quando houver projeção positiva local, faça a rota de catálogo retorná-la sem HTTP ou obtenção de credencial. Valide hosts e identificadores compostos pela fonte aprovada; registros sem URL operacional não devem ser promovidos por inferência de nome. Valide todos os aliases de seleção também no transporte inferior, não apenas no wrapper.
5. Mantenha o teste de requisição e o de resposta separados. Seleção positiva antes de HTTP é a proteção principal; rejeitar payload contraditório antes do consumidor é uma verificação adicional, não licença para consultar dados globais e filtrá-los depois.
6. Execute a regressão com o Python da instalação/projeto que possui as dependências dos testes. Para descobrir o interpretador do launcher Hermes resolvido, use `$(dirname "$(readlink -f "$(command -v hermes)")")/python` e verifique que existe antes de usá-lo. Na instalação MGS, a suíte dirigida é:

   ```bash
   PY="$(dirname "$(readlink -f "$(command -v hermes)")")/python"
   test -x "$PY" || exit 1
   "$PY" -m pytest -q \
     /root/mgs-agent/tests/test_mgs_ares_asset_scope.py \
     /root/mgs-agent/tests/test_mgs_domain_scope.py \
     /root/mgs-agent/tests/test_ares_confidentiality_routes.py \
     /root/mgs-agent/tests/test_ares_meta_common_usage.py
   ```

7. Depois das provas negativas offline, faça smoke live somente nos alvos autorizados: identidade e campos financeiros da conta, edge de campanhas, filho cuja conta foi comprovada, atividades, metadados mínimos do app e relatórios SB com publishers explícitos. Registre status e cobertura sem copiar valores financeiros ou payloads sensíveis desnecessários. Não execute canário de criação/ativação para validar uma correção de consulta.
8. Entregue o delta contra a auditoria original, as mudanças realmente aplicadas e o limite dos testes. Se a separação de arquivos, cofre ou contexto ainda não foi implantada, mantenha o aceite de confidencialidade aberto e apresente a confirmação crítica exata, sem pedir ao operador que redefina o escopo.

## Verificação mínima

- Suites do cadastro e do domínio passam, sem considerar isso prova E2E.
- Provas negativas não usam credenciais nem rede.
- Relatório e checkpoint não contêm identificadores privados ou amostras de payloads reais externos.
- App/permissões/campanhas permanecem intactos durante a auditoria.
