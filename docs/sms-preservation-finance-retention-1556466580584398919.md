# Decisão vigente — preservar SMS e revisar resíduos financeiros

## Autoridade e precedência

Rodolfo Mattei, Discord ID `344196393512075265`, mensagem `1556466580584398919`, thread `1555572634228490283`. Esta decisão supersede a pendência de escolher proteção de propriedade/consentimento do telefone e integridade dos links SMS nesta iniciativa. A aprovação do modelo de limpeza é autorização de preparação/classificação, não autorização de exclusão nem de um cron destrutivo.

## SMS — propostas retiradas por decisão do dono

- Não implementar código de confirmação recebido no telefone (OTP).
- Não adicionar os filtros contra abuso propostos no backend do cadastro SMS.
- Não implementar assinatura, token ou restrição contra adulteração dos links propostos para o fluxo SMS.
- Não alterar por esta iniciativa cadastro, formulário, consentimento atual, telefones repetidos, listas, mensagens, URLs, parâmetros, cliques, envio ou avanço das sequências SMS.
- Não criar a nova camada de observação proposta como alternativa por associação à recusa. Monitoramentos existentes permanecem como estão.
- Preservar os controles preexistentes; esta decisão retira novas intervenções, não manda desinstalar validações existentes, desfazer proteção de CSV ou desfazer os downloads dos agentes.
- Os dois achados históricos de SMS passam a `excluded_by_owner_decision`, não `fixed`/`mitigated`: propriedade do telefone e autenticidade dos cliques não foram comprovadas por uma nova proteção. Não continuar pedindo aprovação para esses mesmos itens como se ainda estivessem pendentes. Só reabrir a intervenção com instrução nova explícita de Rodolfo; um incidente real pode ser diagnosticado/reportado sem autorizar automaticamente uma mudança no fluxo.

## Resíduos financeiros — modelo de revisão aprovado

Escopo: somente cópias volumosas e reproduzíveis de testes encerrados do financeiro. Não se estende a todo o disco, backups de sites, runtimes Hermes, browser profiles ou outros projetos.

1. Manter a prevenção de cópias desnecessárias já instalada.
2. Preservar produção, bancos, saldos, histórico, configurações, relatórios oficiais, evidências compactas, recuperação necessária e qualquer dado único.
3. Revisar cópias descartáveis após 7 dias do encerramento VALIDADO do trabalho que as criou. Idade/mtime/tamanho isolados não provam encerramento nem redundância; prazo apenas abre revisão.
4. Exigir origem/encerramento comprovados, ausência de processos/dependências/mounts/symlinks relevantes, recuperação preservada e revalidação imediatamente antes de propor remoção. Sem comprovação, preservar.
5. Preparar lote fechado com caminhos exatos, motivo, tamanho/espaço recuperável sem inflação por hardlinks, dependências e conjunto retido. Congelar o manifesto real antes da confirmação destrutiva.
6. Pedir confirmação Critical Subset para cada lote exato. O "acho que tá ok" do modelo não substitui essa confirmação nem aprova os 18 diretórios anteriores.
7. Não instalar cron de exclusão automática nesta etapa. Após eventual remoção autorizada, validar ausência exata dos alvos, recuperação preservada, funcionamento e espaço real; registrar/auditar/reportar.

## Estado desta decisão

Persistência institucional e preparação de revisão apenas. Nenhuma alteração de código/configuração SMS ou exclusão financeira executada por esta decisão. Os 18 alvos históricos continuam preservados; refresh de metadados fica em `backups/retention-policy-1556466580584398919/review-metadata.json`. Esse arquivo não é manifesto de exclusão aprovado e não certifica dependências completas.

Fonte anterior dos 18 alvos: `backups/security-round-1556332890743115850/finance/preservation-manifest.json`. Resultados já concluídos de downloads e financeiro permanecem em suas fontes próprias. A revisão autorizada por `1556470980120150179` foi concluída em 18/18, com zero candidatos de descarte comprovado e todos preservados, sem exclusão/cron ou confirmação pendente. Resultado vigente: `docs/finance-retention-review-1556470980120150179-result.md`, supersedendo somente o estado anterior de revisão aberta. SMS, campanhas e CTAs permanecem fora da intervenção por decisão do dono.
