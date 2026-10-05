# Segurança e continuidade — escopo vigente

## Autoridade e continuidade

- Dono: Rodolfo Mattei, Discord ID `344196393512075265`.
- Thread única: `1555572634228490283`.
- Autorização original dos 18 itens: `1556014718810853448`.
- Decisão posterior, vigente para esta intervenção: `1556086886655725599`.

## Decisão vigente: não intervir nos CTAs

Rodolfo determinou: “Não mexe nada de cta não. O que tá nos artigos tá certo. Não precisa mexer com isso. Vamos para o próximo passo.”

Nesta iniciativa, o item 7 (validação/restrição de links editoriais e CTAs) foi retirado da execução por decisão expressa de Rodolfo. Preservar texto, aparência, URLs, destinos e redirecionamentos dos CTAs existentes. Não promover a candidata de allowlist de origem oficial/parceiros, reescrever botões, bloquear destinos, revisar artigos ou criar uma exigência de aprovação de links sob esta rodada.

O finding histórico de URLs de CTAs permanece histórico, marcado como `excluded_by_owner_decision`, não como vulnerabilidade corrigida nem como incidente real demonstrado. A afirmação de que os artigos estão corretos é a decisão do dono, não resultado de uma auditoria adicional dos artigos.

Esta decisão supersede, nesta iniciativa, o item 7 do plano e a proposta do Zeus de permitir apenas origem oficial/parceiros confirmados. Não cancela as outras proteções e validações anteriormente autorizadas. Uma instrução futura explícita de Rodolfo poderá definir outro escopo.

## Escopo atual — Rodolfo `1556332890743115850`

Esta revisão supersede a etapa anterior de observação, concluída e validada.

- Item 2 retirado da intervenção: preservar integralmente as regras e autorizações atuais do Ares; Rodolfo resolverá com Ares eventuais problemas de ligar/desligar campanhas. Não promover a candidata de nova aprovação de campanhas nem alterar o engine por este item.
- Histórico dos itens 5 e 6: na mensagem `1556332890743115850` Rodolfo pediu explicação; `1556336633480089792` autorizou o item 6. O estado antigo de item 5 não autorizado foi supersedido por `1556448396171022478` (continuação) e pela confirmação crítica específica `1556452175473803376`: instalar proteção de downloads nos dois runners REC/P1 e no helper Atena `search-card-image.sh`, com transporte público dedicado e backup/readback. Item 5 instalado e validado conforme `docs/download-protection-1556452175473803376-result.md`; não autoriza mudanças de CTAs, SMS ou exclusões.
- Itens 9, 10, 12, 13, 16 e 18: execução autorizada, respeitando Critical Subset. Item 13 autoriza investigação e manifesto exato, não remoção automática.
- Item 7 permanece excluído e CTAs preservados.
- Sem exclusões, alterações de credenciais/permissões/billing, arquivos de sistema, reboot, mudança de regras de campanhas ou nova rodada de scan/reset. Alterar skills de outros agentes exige confirmação adicional com alvos exatos.
- A frente financeira usa Astra-900k em continuação local foreground, sem alterar o modelo global, e o controlador canônico para eventual promoção. Dados, saldos, histórico e importadores não serão reprocessados para tratar disco.
- Fechamento consolidado distinguirá instalado/validado, candidatos, exclusões de escopo e bloqueios reais; não declarar todos os 18 itens corrigidos.

## Decisão vigente — Rodolfo `1556466580584398919`

Esta seção supersede somente a pendência de SMS e o estado de retenção sem modelo definido; demais entregas/gates ficam preservados. Fonte: `docs/sms-preservation-finance-retention-1556466580584398919.md`.

- SMS: propostas de OTP/código no telefone, filtros novos de abuso no cadastro e proteção contra adulteração dos links retiradas por decisão expressa do dono. Preservar cadastro, captura, listas, URLs, envio e sequência atuais. Não aplicar alternativa de observação por associação. Não desfazer controles anteriores. Achados SMS = `excluded_by_owner_decision`, não corrigidos nem aguardando aprovação.
- Retenção: modelo de revisão manual dos resíduos reproduzíveis de testes financeiros aceito; revisar somente após 7 dias do encerramento comprovado e validado, preservando produção, dados únicos, evidências compactas e recuperação. Prazo não é elegibilidade automática.
- Nenhum lote de exclusão aprovado. Preparar lista exata e congelar manifesto antes da confirmação Critical Subset; sem cron destrutivo. Os 18 diretórios anteriores permanecem protegidos até prova e confirmação do lote.
- Próxima frente aberta: somente retenção/classificação financeira e eventual confirmação de limpeza; não reabrir SMS, campanhas ou CTAs sem nova instrução explícita.

## Fontes atuais

- `data/agent-checkpoints.json`: `ZEUS-ALL-FOLLOWUP-1556014718810853448`.
- `backups/security-followup-1556014718810853448/progress-18.json`.
- `backups/security-followup-1556014718810853448/finding-matrix.json`.
- `reports/performance-followup-1555742041789440011-24h.md`.

Não declarar a iniciativa inteira concluída enquanto as outras integrações e validações permanecerem abertas.
