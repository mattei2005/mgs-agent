# Pagamentos — Editar/Excluir geral

Autoridades Rodolfo 1551662555783635014 e 1551700964975714437; thread1545426987756298340. Implementação publicada/validada. Atribuição Openzed não alterada; principal/gestor continuam Ícaro, dashboard Isliago conforme reclassificação anterior, explicada na origem.

## Entrega
- Botão Editar por lançamento; Opções contém Editar/Excluir; diálogos mostram beneficiário, referência e impacto. Editar suporta descrição/valor/data/natureza.
- Recurso genérico por competência, não duplicação mensal: agosto2026 a dezembro2027, todas17disponíveis; futuros períodos registrados reutilizam a mesma rota/interface. Janeiro–julho fechado continua protegido.
- Removidos seis anulados da exibição, sem exclusão física; cinco créditos Geizian ativos89960centavos preservados. Nenhuma escrita financeira produtiva, nenhum pagamento executado, nenhuma planilha alterada.
- Exclusão usa marcação interna preservada e retira item do cálculo/lista. Audit guarda antes/depois atômico; edição com row lock, fingerprint, escopo do próprio item e confirmação. Owner escreve, partner somente proposta aprovada pelo owner, managers somente própria leitura.

## Evidência real
- TDD RED por módulo ausente, depois GREEN.
- Node full:162casos,161PASS,0FAIL,1SKIP preexistente (August live replay opcional); Python112PASS. npm audit produção:0vulnerabilidades.
- PostgreSQL restoreisolado: edit/delete e saldo testados nas17competências, replay/revisão obsoleta bloqueados,10negaçõesmanager, partner proposta/owner aprovação usando payload armazenado, audit before/after, cenários intactos.
- Navegador público autenticado:17competências,1440px/390px, modais Editar/Excluir abertos e cancelados,0errosJS,0POSTfinanceiro,6antigos ocultos,5ativos899.60.
- Fingerprint ledger/cenários igual antes/depois do deploy; serviços socket/app/PostgreSQL ativos; health ok=true,mode=production,production=true.
- Código em produção idêntico aos hashes:
  - finance-ops.mjs: c508adeab687f58d140b600cc22725fc9db49425aef67afba763fcf2c0aa6d06
  - ledger-edit.mjs: cb486f12fea0f32df70aeea3e83f8ccb07064dcd9b4a4c118c8089d944269306
  - public/operations.js: 3ea827c1b191591fbe4fb2c2c067d97071d41a609fc9cfad4d7456de20c72333
  - public/operations.css: 25d3aba8f667abedc5fd084c533bd1a90d8e48e50be5183a0cca026a6af5b24f

## Recuperações e limites
- Rodada inicial Node encontrou expectativa antiga `not_running.length=7` contra8sites na fonte canônica vigente. Teste corrigido para conjunto explícito de nomes (sem mudar regra/source/runtime); suíte completa rerodada verde.
- Chamada agregada Node+Python excedeu420s; Python foi rerodado separadamente e concluiu112casos em361s. Não houve replay de mutação.
- mgs_pg não atravessava home privado do runtime Node. Copiado binário para stage, mesma versão/hash; nenhuma permissão do home foi alterada. Teste isolado reexecutado integralmente.
- Um teste opcional de replay liveAugust ficouSKIP; não é contado comoPASS. Operações mutáveis foram exercidas no restore, não na produção.

## Backup, rollback e resíduos inventariados
- Workspace protegido: /root/mgs-agent/apps/finance-system/private/payments-edit-1551700964975714437
- Backup PG custom e código antes do deploy com cópia local/remota e SHA-256 igual: /home/zeus/mgs-finance-backups/gam-email/2026-09-21-305e7c65deaa-complete-cb486f12fea0; locais mgs_finance-before.dump/code-before.tar.gz.
- Stage retido: /var/tmp/mgs-ledger-edit-1551700964975714437; DBisolado retido:mgs_finance_ledger_1551700964975714437. Contém somente testes sobre restore; descarte exige autorização específica, não executado.
- Rollback: parar socket+serviço, restaurar somente três arquivos antigos do code-before.tar.gz; reiniciar ambos e validar health/UI/fingerprints. Módulo novo pode ficar inerte; não restaurar banco vivo nem remover auditoria.
- Mudanças docs/skill/registry/checkpoint/audit/inventário registradas. Fonte canônica docs/finance-system-product-direction.md; skill mgs-finance-dashboard/references/payments-approvals-nicolas-pilot.md.
