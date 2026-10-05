# F011 — retirada final validada

## Autoridade e escopo
- Rodolfo: isolamento/proteção `1556720208696316077`; confirmação crítica final `1556731764217618587`.
- Manifesto imutável: `data/f011-apply-1556720208696316077/manifest.json`; SHA-256 `d60cdc70fea3a5a446570a42fada9f37fa5479a6ce50c186be45c40264cd39dd`.
- MatteiInc02, RunCloud servidor `288158`, IP `162.55.28.179`.
- Itens 1–4 protegidos integralmente; itens 5–6 isolados e preservados; retirada somente de 7–8 e seus restores especificados.

## Resultado real
- `streamcb`, banco ID `1342038` e conta `streamcb@localhost`, usuário ID `1209424`: ausentes no MariaDB, em GET individual RunCloud (404) e nos catálogos.
- `mgpchat_5182`, banco ID `1276128` e conta `mgpchatuser_5182@localhost`, usuário ID `1146906`: mesmas verificações de ausência.
- Dois restores autorizados: ausentes.
- RunCloud DELETE usou explicitamente `deleteUser=true`; resíduos de usuário no runtime foram reconciliados somente dentro da lista autorizada.
- As 15 Web Applications, 15 identidades SQL e 15 verificações HTTPS passaram antes/depois. Serviços, bancos, contas e grants não-alvo preservados.
- Grants das quatro contas OpenZed/Cliquet inalterados; isolamento AllAutolan/DatingHubPro inalterado.
- Contas de aplicação globais restantes: **4**, exclusivamente as protegidas por ordem do dono. F011 geral não foi declarada totalmente remediada.
- Recibo: `data/f011-apply-1556720208696316077/retirement-closure.json`; fases privadas individuais mantidas no mesmo diretório.

## Retenção e descarte
- Dois dumps em `/var/backups/mgs-f011-remaining-1556720208696316077`, root-owned e `0600`, hashes/bytes/gzip/restore verificados.
- Manter durante todo o dia **2026-11-04**, America/New_York.
- One-shot Zeus **`be0c6fd23c82`**, `2026-11-05T00:05:47-05:00`, no-agent, entrega à thread `1551768281688580096`.
- Os 47 segundos apenas escalonam a execução dentro do minuto 00:05 confirmado; o calendário global de oito datas foi examinado. Há ticks concorrentes, explicitamente documentados — não se alegou janela livre. Sem alteração dos outros jobs.
- Gate fail-closed: instrução posterior do dono/hold/Discord indisponível/deriva de path, hash, bytes, mode ou links bloqueiam o descarte; nenhuma extensão de escopo.
- Core e runner duráveis em `scripts/f011-retirement-backup-purge-core.py` e `scripts/f011-retirement-backup-purge.py`; wrapper no profile Zeus. Manifesto, plano e core pinados; locks local/remoto, recibo privado e readback independente.
- **11 testes sintéticos PASS**, incluindo 9 gates negativos, dry-run e remoção/replay real apenas de fixtures; nenhum dump de produção removido nos testes.
- Live dry-run com transporte real PASS; `--apply` antes do prazo apenas confirmou retenção. Nenhum purge antecipado.
- Backups de `soluc3_1`, `streamcb_480100`, Pine e rollback de grants não pertencem ao descarte.

## Falhas de validação recuperadas
- Primeiro smoke do runner falhou no acesso 1Password: o processo não havia carregado o `OP_SERVICE_ACCOUNT_TOKEN` já existente na fonte canônica. Carregamento corrigido; nenhuma credencial criada/alterada/rotacionada; smoke e live dry-run reexecutados PASS. Recibo falho preservado separadamente.
- A primeira comparação de jobs incluiu `repeat.completed`, que avançou normalmente durante a tarefa. Validador corrigido para comparar apenas estrutura e `repeat.times`; readback exato e preservação dos outros jobs PASS.
- O tool cron não possui ação `get`; readback foi realizado por `list` e pelo registro exato persistido, sem nova criação.
- Skill Hermes desabilitada no loader: documentação canônica e skill local foram consultadas em leitura, sem habilitar ou alterar o profile.

## Continuidade
- Nova decisão canônica vinculada à confirmação final, com supersessão explícita da anterior.
- Planilha: 10 células em Resumo/Prioridades/Servidores atualizadas com valores e apresentação conferidos; inventário e checkpoints atualizados, registry com única versão ativa e supersessão explícita, auditoria registrada e validação institucional PASS.
- REPORT-INFRA `1556740435873894431`, canal `1498132022634483894`: embed direto com content vazio/sem mentions, readback exato PASS.
- Skill `application-database-retirement-governance`: gates do one-shot, carregamento do ambiente já existente e distinção de configuração versus contadores do cron salvos e conferidos.
- Escopo autorizado atual concluído; descarte dos dumps permanece futuro e condicional, sem execução antecipada. As quatro contas protegidas mantêm o risco residual da F011 geral.
