# Boostingecon, recuperação diária e regra de primeira falha

## Autoridade

- Boostingecon: Rodolfo `1548317688051277918`.
- Regra operacional: Rodolfo `1548326753615876227`.
- Thread: `1545426987756298340`.

## Decisão aplicada

- Placement literal: `pl_digital-trust_boostingecon_us`.
- Site: Boostingecon.
- País/vertical: US / `us-cc-en`.
- Gestor/operação: sempre MGS `g002-d`, exclusivamente estratégia de bot.
- Estado mensal desde setembro/2026: `Não participa` do rateio das Despesas Gerais.
- Receita orgânica residual continua nos resultados mesmo quando o site não está em operação.

## Produção

- Boostingecon foi registrado em 16 competências, setembro/2026 a dezembro/2027.
- Estado interno: `INATIVO`, `SEM_COMISSAO`, US, CAD, SB Rede1; apresentação pública: `Não participa`, MGS.
- Unidades ativas e caixa permaneceram idênticos durante o cadastro do site.
- Recuperações bloqueadas: `recovery-current-policy-1548317688051277918-*`.
- Serviços financeiros permaneceram ativos; nenhum restart.

## Pipeline diário de 11/09

- Gastos Meta/Google: status final `ok`, cobertura até 11/09, `failure_streak=0`.
- Receita GAM: 2.480 linhas → 60 grupos.
- Totais-fonte preservados: CAD `20589.60661244756023753937`; USD `6524.6875898867087362474`.
- Importação: revisão 144→145, audit 725, recovery `recovery-gam-email-2026-09-11-aa6f539734a2`.
- Cutoff: 10/09→11/09.
- Replay posterior: `already_applied=true`, sem duplicação; revisão 146 foi reconciliada com `AUTO_QUOTES_UPDATED` audit 727, não com nova importação.
- Próxima data esperada no state: 12/09; blockers e falhas antigas limpos.

## Falhas investigadas e corrigidas

1. O ciclo de gastos das 09:03 encontrou três respostas Meta temporariamente inconsistentes; a repetição confirmou duas como transitórias.
2. Yolokfx G006 retornou soma diária USD 1.757,66 e agregado USD 1.757,60. Causa: Meta arredonda cada dia e o agregado separadamente. O limite fixo de USD 0,01 era inválido para uma janela de vários dias.
3. A coleta e o importador Node agora usam a mesma tolerância matemática explícita: `0,005 × (dias retornados + 1)`, limitada a USD 0,16 por mês. Google continua com reconciliação exata; diferença acima do limite bloqueia.
4. O primeiro retry chegou ao importador, mas falhou porque somente a camada Python tinha sido corrigida. A camada Node foi então corrigida, homologada e publicada com backup; o retry integral seguinte concluiu gastos e receita.
5. Validações de navegador inicialmente esperaram metadados que a API resumida não expõe e usaram uma rota histórica. O teste foi corrigido para validar metadados na adição PostgreSQL e apresentação na rota pública atual; produção não foi alterada por essas falhas de teste.
6. Um diagnóstico inicial omitiu o carregamento do ambiente 1Password e falhou fechado; foi repetido pela rota canônica sem expor credenciais.
7. Na checagem final, um timeout digitado incorretamente promoveu um comando curto para background rastreado com notificação. O processo foi consumido antes do encerramento e o readback da thread confirmou que nenhum output bruto separado foi publicado. A mesma checagem consultou `systemctl` no host local e mostrou unidades inativas que pertencem ao RunCloud; a validação foi refeita no alvo correto e confirmou os três serviços remotos ativos. Nenhuma das duas falhas alterou produção.

## Regra permanente de Rodolfo

O SOUL do Zeus agora determina intervenção desde a primeira falha: investigar causa-raiz, corrigir com segurança dentro da autoridade vigente, repetir, validar a recuperação e avisar Rodolfo somente após recuperação integral ou diante de bloqueio decisório/Critical Subset. A preferência também foi salva em USER. A compactação automática de capacidade reduziu USER de 96% para 88,92%, preservando a regra; report de limites `1548335013982904451`.

## Validação

- 131/131 testes Node.
- 92/92 testes Python.
- Sintaxe Python/Node aprovada.
- Homologação da política: 16 competências, idempotente, caixa/unidades ativas imutáveis.
- Homologação e produção do spend importer: dry-run PASS, zero source/API query errors.
- Browser owner 1440 e 390: Boostingecon visível como `Não participa`, MGS, uma receita em 11/09, zero erro JavaScript e zero overflow.
- SQL source readback: `us-cc-en`, `g002-d`, CAD e source hash preservados.
- GAM dry-run pós-fechamento: espera 12/09 e não altera state.

## Backups e evidência

- Código/política + PostgreSQL: `/home/zeus/mgs-finance-backups/1548317688051277918/`.
- Backup DB SHA-256: `9416fb392985fed58116c742d79ffc3e8f37fcb80a28341cdff52c9c34d1cd04`.
- Backup do importador de gastos SHA-256: `4cac8a81b2ef30d4d7741f4115de90c0836cb686704abe2c28b7894ad3dfe789`.
- Backup GAM: `/home/zeus/mgs-finance-backups/gam-email/2026-09-11-aa6f539734a2/`.
- Evidência local: `/root/mgs-agent/apps/finance-system/private/boostingecon-policy-1548317688051277918/`.
- Run final GAM: `/root/mgs-agent/apps/finance-system/private/gam-email-runs/20260912T094940-0400/`.
