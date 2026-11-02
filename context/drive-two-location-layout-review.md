# Revisão da separação entre entrada MGS e arquivo de 30 TB

## Pedido e fronteira

- Rodolfo Mattei, Discord `344196393512075265`, mensagem `1566810303168254075`, thread `1562078493498540042`.
- Pedido executado: conferir todas as pastas nos dois locais e explicar a divergência. Direção expressa: Drive MGS com a entrada UPLOAD MANUAL, sem árvore de nichos/gestores; todo o arquivo organizado nos 30 TB.
- Esta revisão é somente leitura remota. Não autoriza implicitamente mover/excluir arquivos, mudar credenciais/ACL, editar skills de outro agente, interromper writers ou criar campanhas. Nenhum desses efeitos foi executado. A revisão não ativa uma topologia nova; o intake anterior permanece tecnicamente ativo até cutover validado.
- Evidência: `data/ares/creative-ops/30tb-archive/two-drive-audit-1566810303168254075/`.

## Cobertura nativa validada

- MGS-AGENTS (`0AEwt4Ye690ocUk9PVA`): 158 pastas, incluindo UPLOAD MANUAL e todos os descendentes. A raiz foi relida sem mudança de IDs durante a auditoria: UPLOAD MANUAL, três Sheets e um ZIP.
- Nos 30 TB: MGS-ARQUIVO (`1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`) com 1.653 pastas descendentes e MGS-CORPORATIVO (`16fP9b4bp3inB1Gze95znQLYq3rdtTEhp`) com 13. Não incluir as duas raízes nesses números.
- Total de pastas descendentes nos três escopos: 1.824. Validação independente em 63 lotes, 1.827 parents examinados, todas as páginas consumidas, zero divergência de conjuntos de IDs. Prova `folder-parent-closure-verification.json`.
- Consulta por owner não era inventário completo: doze pastas de Usados em árvore legada pertencem a gestores, não ao Gmail de arquivo. Consulta corpora=user também não cobriu todas as pastas do Shared Drive; união com corpora=drive e fechamento por parent resolveram a cobertura, sem mover nada. As mídias inicialmente projetadas fora da árvore por owner foram localizadas sob essas pastas de gestores; não eram perda nem arquivo solto.
- O inventário cobre as raízes MGS compartilhadas e acessíveis à SA, não conteúdo pessoal não compartilhado de toda a conta. Não foram encontrados outros folders visíveis fora desses escopos após a união correta. Foram consultados metadados e árvore, não refeita a verificação integral dos bytes do acervo.

## Achados para decisão

### 1. A entrada também tem uma árvore por nicho e gestor

Problema: UPLOAD MANUAL contém 19 pastas de operação e 114 pastas de gestor, além de processamento temporário e material fora dos slots. Isso explica a repetição visual entre entrada e arquivo; não prova duplicação de bytes.

Causa confirmada: o desenho anterior criou slots operação/gestor para fornecer contexto seguro ao intake. `ares_upload_context_layout.py::validate_slot` exige esses parents, e `ares_autonomous_intake.py::validate_new_batch` valida o mesmo binding. A implantação dessa estrutura foi conduzida por Zeus, não é mudança não atribuída de terceiros. A preferência atual é uma entrada mais simples, sem essa árvore permanente.

Solução recomendada, ainda não implantada: usar o pedido/lote autorizado como fonte explícita de operação, gestor e destino; habilitar entrada simples mantendo o mesmo link, preservando isolamento e fail-closed para contexto ambíguo. Adaptar produtor, descobridor, claims, tratamento, arquivo, conclusão e retirada antes de deslocar a árvore. Mover pastas primeiro quebraria guards atuais. Toda área técnica temporária deve continuar temporária, sem virar estoque ou segunda organização permanente.

### 2. O Drive MGS voltou a ter arquivos permanentes na raiz

Problema confirmado: três Sheets e um ZIP, fora de UPLOAD MANUAL. Nomes/IDs e metadados nativos estão no inventário. Foram criados depois do aceite histórico da migração; por isso aquele aceite não descreve o estado atual. Não atribuir criação a uma pessoa apenas por lastModifyingUser.

Solução recomendada: conferir dependências e realocar os mesmos IDs para destino de relatórios/referências nos 30 TB, preservando links, fórmulas, permissões e consumidores; corrigir destinos futuros dos produtores correspondentes. A presente auditoria não autoriza essa escrita nem classifica esses arquivos úteis como lixo.

### 3. Há conteúdo fora do padrão e conteúdo temporário que não pode ser descartado por aparência

- Treze imagens diretamente em UPLOAD MANUAL.
- Oito pastas de nome numérico na árvore, sete no primeiro nível e uma aninhada; nenhuma contém arquivo na enumeração.
- Dois arquivos em um slot registrado e 91 arquivos abaixo da área de processamento; esta tem 16 pastas incluindo sua raiz. São classes distintas, não somar como criativos independentes nem presumir que todo material precisa novo tratamento.

Causa de cada colocação/estado não foi atribuída nesta auditoria. As pastas numéricas são anteriores à implantação atual; data de criação não identifica autor do movimento. Material fora dos slots não pode receber operação/gestor por adivinhação.

Solução recomendada: conciliar arquivos por ID/linhagem/claim/recibos e reservas antes de destinação; preservar o que já foi tratado/arquivado, sem reprocessar ou recópia. Descarte de pastas vazias continua sujeito à confirmação crítica exata, não à aparência.

### 4. A parte principal do arquivo está no local esperado

MGS-ARQUIVO contém CRIATIVOS e _MGS_CONTROLE. Em CRIATIVOS, o estoque por operação/formato/READY/Exclusivos/Usados convive com LIBRARY META, 00_ARQUIVO_CONTROLE e _ARQUIVO_FISICO; esses grupos têm funções diferentes e não devem ser mesclados pelo nome. MGS-CORPORATIVO contém planilhas/referências e as classes separadas _DISASTER_RECOVERY e _DR_LEGADO. A imagem enviada corresponde a essas raízes de 30 TB. Não é evidência de que controles/backups estejam no Drive de entrada, nem autorização para apagar ou fundir tais pastas.

## Desenho recomendado para revisão do Rodolfo

- Drive MGS: somente UPLOAD MANUAL como entrada simples; arquivos somente enquanto aguardam tratamento/arquivo seguro. Sem árvore permanente por nicho/gestor ou relatórios definitivos na raiz.
- Drive 30 TB: MGS-ARQUIVO para criativos e controles; MGS-CORPORATIVO para relatórios, referências e backups, preservando a separação de acessos.
- Nicho, formato, gestor, Exclusivos e Usados aparecem na organização definitiva, não como pré-requisito de pasta para quem envia.
- Upload e pedido ao Ares fornecem o contexto; campanha só segue autorização própria. A confirmação futura do primeiro uso Exclusivos→Usados continua distinta desta revisão.

## Estado ao fechar a auditoria

Inventário de pastas completo e diagnóstico persistidos. Nenhuma pasta/arquivo remoto foi movido, excluído ou renomeado. O desenho simplificado é recomendação/expectativa em revisão, não implantação certificada. Mudanças de mecanismo, outros agentes, compartilhamento e descarte continuam com seus gates específicos.
