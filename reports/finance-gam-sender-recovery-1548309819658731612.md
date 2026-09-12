# Recuperação do intake GAM direto — 12/09/2026

- Autoridade operacional: Rodolfo `1547983130038767755`; correção/evidência de chegada `1548309819658731612`.
- Thread: `1545426987756298340`.
- Incidente: o par de 11/09 chegou às 08:00 Eastern, mas o coletor aceitou somente o remetente do encaminhamento manual e publicou um falso alerta de par ausente.
- Causa-raiz: entrega diária direta usa o endereço parseado exato `admanager-noreply@google.com`; o contrato esperava apenas `contato@marketingdigitalad.com`.

## Correções

- Allowlist exata passou a aceitar o remetente direto GAM e o encaminhador manual de recuperação.
- Criado `--manual-intake`, que ignora somente o relógio e preserva toda a cadeia intake → gastos → receita.
- Dry-run passou a não alterar state nem notificar.
- Resultados saudáveis da caixa limpam flags técnicas antigas; bloqueio empresarial não conta como falha técnica.
- Reutilizados mapeamentos já validados em setembro: Cliquet/GB, Cephyric/FR e o token `topfeedfun` para TopFeed.

## Validação real

- IMAP `BODY.PEEK` read-only confirmou o par direto de 11/09:
  - USD: recebido `2026-09-12 08:00:30 Eastern`, 15.319 bytes.
  - CAD: recebido `2026-09-12 08:00:09 Eastern`, 154.444 bytes.
- Ambos os anexos validaram data financeira `2026-09-11`.
- Fonte: 2.480 linhas; CAD `20589.60661244756023753937`; USD `6524.6875898867087362474`.
- Testes: 130/130 Node; 90/90 Python; sintaxe/JSON aprovados.
- Dry-run: hash do state idêntico antes/depois.
- State final: `blocked_mapping`, `failure_streak=0`, `intervention_required=false`; aviso readback `1548313066838564966`.
- Produção financeira: zero writes; PostgreSQL permanece revisão 140 e cutoff `2026-09-10`.

## Bloqueio legítimo restante

A única linha ainda sem classificação canônica é `pl_digital-trust_boostingecon_us`: 1 impressão, sem UTM/campanha, CAD `0.0000884741761102122`. É necessária decisão de Rodolfo sobre site/vertical/gestor/operação. Até lá, o cutoff não avança e nenhum valor de 11/09 é aplicado.

## Evidência

- Run corrigido: `/root/mgs-agent/apps/finance-system/private/gam-email-runs/20260912T084318-0400/`
- Backup de código/config: `/root/mgs-agent/apps/finance-system/private/gam-sender-recovery-1548309819658731612/before/`
- Auditoria auxiliar: `/root/mgs-agent/apps/finance-system/private/gam-sender-recovery-1548309819658731612/`
