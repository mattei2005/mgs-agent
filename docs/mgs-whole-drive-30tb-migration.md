# Migração integral MGS-AGENTS → conta de 30 TB

## Autoridade e supersessão

Rodolfo `344196393512075265`, thread `1562078493498540042`, definiu o novo escopo em `1562459142814306425`, recebeu a explicação do desenho e autorizou iniciar em `1562459803186626571`. Objetivo: migrar TODO o conteúdo do Shared Drive `0AEwt4Ye690ocUk9PVA`, não apenas CRIATIVOS, para a conta `mgsdigitalcorp@gmail.com`; deixar no Drive empresarial somente a entrada `CRIATIVOS/UPLOAD MANUAL`, suas pastas-pai e a estrutura temporária estritamente necessária; tratar via Ares, arquivar original+tratado, validar e liberar staging após pelo menos 24h da verificação/liberação do processamento. Sem mensagens de progresso; informar apenas 100% validado, necessidade real de editor Apps Script ou bloqueio de segurança/Critical Subset.

Esta fonte supersede o limite anterior de migração apenas criativa para o objetivo integral; a migração criativa já autorizada permanece válida e continua pelo mesmo writer/locks. Não ampliar implicitamente o manifesto histórico criativo nem sua política de exclusão futura. O pedido autoriza implementação e migração; não dispensa confirmação crítica de exclusão/credenciais/permissões novas ou alteração de skills de outros agentes.

## Descoberta integral real

Evidência: `data/ares/creative-ops/30tb-archive/whole-drive-migration-1562459803186626571/{inventory.json,discovery.json,source-access.json}`.

O inventário inicial completo/paginado contém 7.884 objetos ativos e 228.215.846.168 bytes reportados, sem parents não resolvidos. A árvore CRIATIVOS tem 7.771 objetos; `_DISASTER_RECOVERY`, 102 objetos e 200.820.560.275 bytes, com 97 arquivos criptografados. Existem oito planilhas nativas, distribuídas pela raiz, Meta Utility Templates e referências da Atena. O conjunto pode avançar por produtores autorizados; revalidar antes de mutações, nunca congelar o universo futuro pelo número de hoje.

## Invariantes

- Usar exclusivamente SA canônica para agentes; owner Apps Script isolado já aprovado para operações que exigem propriedade/cota Gmail. Sem token pessoal, OAuth alternativo, consentimento de navegador ou mudança de autenticação.
- Preferir recursos/IDs preservados para Sheets, links, atalhos e backups; provar por canário antes de mover produção entre Shared Drive e My Drive. Cópia de uma Sheet não preserva o ID e não equivale a migrar suas dependências.
- Preservar o acesso efetivo por item, sem ampliar os colaboradores de arquivos restritos. O root Shared Drive tem quatro principais (owner Gmail, Rodolfo, support e SA); o arquivo criativo tem onze principais. NÃO copiar backups criptografados para um pai com nove colaboradores criativos e tratar herança como paridade. Nunca descriptografar backups apenas para migrar armazenamento.
- Preservar criptografia, hashes, catálogo, retenção e restore funcional dos backups. Mudar só destino sem ajustar produtor, retenção, verificadores e recuperação não satisfaz automação integral.
- Preservar fórmulas, IMPORTRANGE, IDs de abas, formatação, permissões e consumidores/Apps Script das oito Sheets. Inventariar dependências antes do cutover; registrar erro preexistente separadamente.
- Preservar IDs lógicos, reservas, catálogo, campanhas e elegibilidade do Ares. Migração de armazenamento não autoriza campanha, budget ou novo tratamento do histórico.
- Nenhum arquivo histórico, pasta, atalho, backup ou Sheet será apagado para forçar fechamento. Exclusão exige o gate aplicável, cópias e consumidores completos, prova contra corrida e receipt real.
- Criativos históricos seguem no protocolo atual até o novo protocolo ser provado e deliberadamente promovido; sem writer paralelo, duplicação ou mudança de escopo dos requests existentes.

## Próxima fronteira do proprietário

O worker Google ativo e seu bootstrap estão limitados a CRIATIVOS. Não conseguem inspecionar/migrar o escopo corporativo por comando SA. Uma extensão hash-pinned precisa ser publicada e deliberadamente repinada no mesmo Code.gs; preservar manifesto, consentimentos e o timer. Primeiro provar capacidades reais do proprietário e o modelo de acesso dos alvos corporativos, sem mover/copiar/deletar produção nesse probe. O fato de a SA mostrar `canMoveItemOutOfDrive=true` não comprova o comportamento ou propriedade resultante quando executado pelo owner Gmail.

## Fases de aceitação

1. Autoridade/escopo e inventário integral, ACL por item e dependências de Sheets/produtores.
2. Extensão owner publicada/testada/relida; repin deliberado e receipt nativo com capacidades/restrições do owner. Não promover pin ativo antes da execução real.
3. Canário de transferência mantendo ID e acesso ou, se inviável, cópia com cutover completo de IDs/dependências e ACL restrita explicitamente resolvida.
4. Migração delimitada das áreas corporativas, mantendo ordem de dependências e recuperação; todos os bytes/objetos conferidos.
5. Ajuste e prova de todos os produtores/leitores/backup/restore/retention para destino de 30 TB; nenhum crescimento permanente no root antigo fora do staging autorizado.
6. Concluir acervo criativo, leitores e atalhos; adequar pipeline para armazenamento antigo apenas temporário abaixo da entrada preservada.
7. Executar somente a retirada autorizada após os gates aplicáveis; verificar árvore residual real e funcionamento integral, então reportar 100% com evidências. Até isso, iniciativa permanece aberta.
