# Direção vigente — mínimo local e prevenção de acúmulo

## Autoridade e precedência

Fonte humana: Rodolfo Mattei, mensagem `1572625943313256503`, thread `1569928464033783862`, 18/11/2026. Executor/dono desta iniciativa: Zeus. O pedido redefine o objetivo da análise: manter localmente somente o necessário à operação e à recuperação atual validada, retirar cópias/resíduos dispensáveis e prevenir reacúmulo. Não é necessário conservar todo estado técnico antigo apenas por ser diferente ou único.

Esta direção supersede a direção de retenção desta iniciativa registrada em `STORAGE-REVIEW-LATEST-ONLY-1570799339108958250` e a pausa de análise de caches em `1571982102264549498` **somente para reabrir a avaliação/desenho de limpeza semanal seletiva**. Não é autorização para apagar um cache inteiro, ativar cron destrutivo desconhecido, descartar histórico vivo/conversas ou remover programas necessários. Nenhum lote anterior deve ser repetido.

A fala é direção e pedido de análise/esclarecimento, não confirmação de manifesto exato. Exclusões, nova retenção destrutiva e demais Critical Subset exigem apresentar alvos/efeitos/retidos e obter a confirmação correspondente. Não elevar a escolha condicional VPS ou Hermes a uma escolha técnica já aprovada.

## Pontos em ordem

### 1 e 2 — Financeiro e testes

Preservar produção, código/configuração realmente consumidos, entradas/idempotência necessárias, trabalhos pendentes e recuperação atual. Identificar por unidade as sobras das tarefas encerradas e retirar os estados de teste desnecessários após checar consumidores. Se o descarte perde um estado histórico de teste, declará-lo claramente; não chamar esse estado de duplicata nem exigir preservar sua totalidade como condição automática quando o objetivo aprovado é aposentá-lo sem afetar a operação atual.

Prevenção deve atingir o produtor: evitar manter nova cópia local integral quando o provedor aprovado e o fallback atual bastarem, e dar destino/encerramento aos artefatos de testes. Estado de erro/parcial ou trabalho em aberto fica retido até reconciliação. Mudar código ou documentar regra não comprova implantação nem economia; validar o consumidor real e a recorrência.

### 3 — Novo backup e aposentadoria dos anteriores

Rodolfo propôs um backup atual completo da VPS **ou** do Hermes e posterior retirada dos antigos. Recomendação: ponto externo atual de recuperação da VPS para o descarte amplo, acompanhado de evidência de recuperação; alternativa delimitada: backup completo e coerente do Hermes (código/customizações, configuração, perfis, conversas, bancos e schedulers), sem afirmar que cobre outros sistemas.

A escolha de modalidade ainda não foi feita. Não criar um tar de `/` na mesma VPS como equivalente a snapshot externo. Antes de retirar antigos: fixar cobertura, geração/ID, integridade, acesso/restore e um teste isolado compatível. Um backup atual sem as cópias históricas não recria estados já sobrescritos; se a opção for um snapshot completo que também contenha os arquivos antigos, mapear isso e não duplicar preservação local sem necessidade. Recuperação mínima não significa manter toda árvore expandida antiga. Definir separadamente o rollback imediato de código que a operação ainda usa e a retenção externa; não apagar bases/alternates por inferência de backup.

### 4 — Mídias dos agentes

A intenção é usar os 30 TB como arquivo definitivo e a VPS como processamento transitório, não manter acervo local duplicado. Essa finalidade já consta em `context/processes.md:137–148`; a topologia posterior nos 30 TB vence a antiga referência a Shared Drive.

As mídias da Meta Library incluem vídeos/imagens de referência/coleta e pacotes, não só os criativos finais tratados. O censo local atual encontrou principalmente MP4/JPG/PNG. A afirmação humana de que tudo está no Drive orienta a conferência, mas cada local selecionado deve ser ligado ao provedor remoto correto por bytes/linhagem/readback antes de sua retirada. Originais/referências não devem ser presumidos cobertos apenas porque o criativo final está entregue. Depois de concluído/arquivado e confirmado o destino, manter índice compacto e liberar somente o binário/workdir transitório. Preservar coletor, Chromium necessário, cookies, perfil e sessão autenticada; não são mídias de entrega. Não mudar elegibilidade/campanhas nem abrir writer paralelo.

### 5 — GitHub

O auto-versionador `mgs-autocommit.service` foi observado active/running/enabled. `HEAD`, `origin/main` e o ref remoto consultado via `git ls-remote` coincidiram em `fe4b09ca44dee4bf25042ca09a5ba18965747bc5`. Havia 33 entradas locais no status, portanto essa igualdade não prova que todo trabalho atual já foi publicado. Há batching nativo.

Nem tudo vai ao GitHub: `.gitignore` exclui bancos, estados runtime, backups, caches e sessões de navegador; o writer também impõe regras de segredo/tamanho/pathspec. A cópia de trabalho local contém código/scripts executados pela VPS; não pode ser apagada só por estar publicada. `.git` é histórico/metadados separado: sua profundidade local é otimizável, não intrinsecamente toda necessária. Uma migração enxuta precisa passar nos testes de auto-versionamento, atualização, rollback, refs, worktrees/alternates e recuperação histórica antes de reduzir o store; não apagar `.git` nem reescrever história remota incidentalmente.

### 6 — Cache semanal

Rodolfo reabriu a avaliação de uma limpeza semanal. A hipótese de que todo cache afeta somente velocidade é incorreta neste ambiente: há binários Chromium, modelos, ambientes gerenciados e perfis autenticados sob raízes com nomes semelhantes a cache. Removê-los pode causar download obrigatório, falha offline, interrupção de automação ou perda de sessão.

Proposta: lista positiva de caches realmente regeneráveis/dispensáveis, recurso não ocupado, locks, native cleanup quando aplicável, preservação dos consumidores ativos, registro de bytes/resultado e validação pós-operação. Fazer simulação antes de ativar. Não instalar `rm -rf ~/.cache` nem um prune UV genérico; o incidente anterior de UV mantém seu modelo incompleto bloqueado. Definir agenda somente após aprovação do recorte e auditoria global de horários. Nenhum cron novo ou limpeza semanal está ativo por este documento.

### 7 — Relatórios de pagamentos

É o material de apoio da atualização da planilha de pagamentos Meta: capturas da tela de billing, snapshots/readbacks da planilha e JSONs/recibos de coleta/publicação/recuperação. Não é uma pasta que execute pagamentos nem o banco de produção do dashboard.

O censo em `reports/meta-manual-payments-runs` encontrou 1.761 PNG (3.068,42 MiB alocados) e 4.014 JSON (971,50 MiB), além de textos/logs/código pequenos; zero erros. Os JSONs grandes observados incluem `initial-workbook`, `final-workbook` e `partial-workbook-readback`. Essa evidência sustenta decisão de quanto é transitório, não exclusão automática. Há execução/recuperação corrente; não interromper nem retirar seus inputs ou provas pendentes.

Execução recomendada: separar evidências de cobranças/valores e último snapshot útil de capturas intermediárias e cópias repetidas; depois da execução encerrada, preservar prova compacta ou arquivo privado aprovado e retirar o peso dispensável sob gate exato. Não enviar conteúdo de billing ou sessão para pasta de criativos com ACL ampla, não executar pagamento e não alterar regra funcional do relatório.

## Entrega e continuidade

Este documento registra a direção atual e responde às sete dúvidas. Não cria backup, cron, migração Git ou exclusão. Próxima execução: preparar um pacote consolidado com (a) retenção/prevenção financeira, (b) backup atual e aposentadoria delimitada, (c) mídia já arquivada, (d) cache semanal seletivo e (e) evidência financeira compacta; separar os itens efetivamente prontos dos dependentes de decisão/prova. Não pedir `continue` por família. Uma confirmação crítica conjunta só pode ser apresentada após inventário, verificadores e testes dos alvos reais. Não prometer execução autônoma após o turno sem consumidor/agendamento verificado.
