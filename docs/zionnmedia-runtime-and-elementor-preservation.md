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
