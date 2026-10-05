# Zionn Media — runtime e preservação do Elementor

## Decisão ativa

- Dono: Rodolfo Mattei. Fonte: mensagem Discord `1556378161510617333`, thread `1556015743831646349`, em resposta à confirmação específica de PHP8.1→8.3.
- Autoriza a migração **somente do webapp zionnmedia.com** no MatteiInc01, com backup, canário validado e rollback se qualquer gate regredir.
- Exclui alterações no Elementor instalado. Preservar Elementor base, Elementor Pro e sua unidade de compatibilidade (PowerPack), incluindo versões, ativação, árvores de arquivos, licença e dados do builder. Não atualizar, substituir, desativar ou migrar os widgets sem nova instrução explícita de Rodolfo.
- Rodolfo informa que não possuem mais a versão paga e prefere preservar o funcionamento. Isso é a justificativa informada pelo dono, não certificação independente do estado de cobrança ou licença no fornecedor.
- Atualizações comerciais deixam de ser um objetivo executável desta etapa; permanecem como risco residual conhecido e explicitamente diferido, não como risco eliminado.
- Preservar as contenções de segurança já validadas. Permissão para migrar PHP não autoriza alterar outros sites, licenças, credenciais ou cobrança.

## Continuidade

Fonte histórica da remediação: `reports/zionnmedia-remediation-20261004.md`.
Evidência do novo corte: `/root/.hermes/profiles/zeus/workspace/zionn-php83-20261004/`.
Checkpoint: `zionnmedia-remediation-20261004`.
Chave canônica: `zionnmedia.elementor.compatibility-unit.preserve`.
Esta decisão substitui o próximo passo anterior de buscar/migrar o Elementor; o relatório histórico permanece preservado.

## Escopo atual — entrega ao proprietário e saída da hospedagem

Fonte: Rodolfo Mattei, mensagem `1556452432932765757`, thread `1556015743831646349`.
Chave canônica desta decisão: `zionnmedia.owner-handoff.priority-scope`.

- O proprietário do site é um amigo de Rodolfo, sem identificação nominal informada. Rodolfo fornece a hospedagem; a autoridade operacional descrita acima não significa que o site seja propriedade da MGS/Rodolfo.
- Rodolfo exclui correções e novos testes do envio de email/formulário. A rejeição SMTP identificada permanece documentada, mas deixa de ser bloqueio para o objetivo de entrega do site.
- Prioridade: resolver somente problemas importantes de segurança e funcionamento; não perseguir score Lighthouse ou outras otimizações cosméticas como condição para entregar o backup. Performance mobile72/100 permanece uma limitação conhecida, não um gate obrigatório de handoff.
- Preservar a unidade Elementor/base+Pro+PowerPack e as contenções MU existentes. As remediações de spam identificado, proteção de rotas e PHP8.3 permanecem documentadas nos relatórios; não converter isso em certificação universal de segurança.
- Plano informado por Rodolfo: ele fará o backup, entregará o arquivo ao amigo e depois excluirá o site do próprio RunCloud. Não foi delegado a Zeus criar/exportar/enviar o backup nem excluir webapp, banco, arquivos, usuários ou DNS neste turno.
- Antes da retirada, a recomendação é validar uma restauração em ambiente do destinatário, incluindo arquivos/banco/MU plugins, PHP compatível e funcionamento das páginas. Backup legível não equivale a restauração funcional. Ao mudar domínio/hospedagem, revisar URLs locais hardcoded e acessos/credenciais incluídos no pacote; não entregar segredos de infraestrutura compartilhada.
- Qualquer exclusão executada por Zeus exigirá confirmação Critical Subset própria com alvo exato e backup/restauração comprovados. O plano de saída não é autorização destrutiva.

Supersessão operacional: esta decisão substitui o objetivo de corrigir SMTP e otimizar mobile do checkpoint `zionnmedia-followup-20261004`; preserva o diagnóstico histórico em `reports/zionnmedia-followup-20261004.md` e não revoga a preservação do Elementor.
