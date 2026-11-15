# AD01 Viewer Loan — diagnóstico bloqueado, sem reparo aprovado

Owner operacional exclusivo: `t_bdfc754f`.
Request preservado: `eggbev-pg23189-1571342489162489937`.

## Resultado e limite comprovado

- GET real com Ana `122147293515218951`, app `953171080682697`, token USER válido; autoridade original/ASAP/thread confirmada pela rota central.
- AD01 `120251246303620629`: PAUSED / WITH_ISSUES; HARD_ERROR `2446386`, MID `e5fad875ff58ee212f01bd3b2d24f754`, creative `1676402284181464`, story `1355561690982225_122098583937552287`.
- Criativo expõe `thumbnail_url` top-level e 2 vídeos AFS, mas não `image_hash`, `image_url` ou AFS `images`. Não é possível inferir que nenhuma imagem interna existe.
- 9 downloads reais HTTP200/JPEG: 3 thumbnails top-level (AD01, AD02 controle, seed AD01), 2 thumbnails AFS AD01 e 4 preferred thumbnails dos vídeos de AD01/AD02. A top-level AD01 é byte-idêntica à seed. Nada disso identifica a dependência interna rejeitada ou invalida HARD_ERROR.
- GET dos dois stories, até somente `fields=id`, falha com HTTP400/code10 citando pages_read_engagement/PPCA. Debug metadata e `/me/permissions` comprovam **pages_read_engagement granted**. Portanto não atribuir o erro a scope ausente nem pedir grant/credencial nova como correção presumida; o controle saudável tem o mesmo erro nessa rota USER.
- Fonte303: diferenças somente na URL nativa de thumbnail, reconciliadas pelo comparador canônico com downloads frescos e bytes iguais (não foi alterada a fonte nem o comparador).

**Causa específica ainda não comprovada:** qual imagem interna está indisponível e por quê. Exclusão, falta de permissão da imagem, materialização interna e interferência humana não foram demonstradas. Não foi instalado contrato de reparo nem concedida autorização para substituir creative/imagem.

## Gate exato e recomendação

Solicitar no Ads Manager ou ao suporte Meta o detalhe de imagem/asset rejeitado do MESMO AD01, fornecendo ad/creative/story/MID acima. Precisamos de referência identificável ao campo/asset rejeitado e seu estado/acesso; não de um novo OK comercial. Usar sessão humana já autorizada; não criar sessão/credencial/grant automaticamente.

Uma rota com token derivado da Page ou outra identidade NÃO foi utilizada: este pedido exige Ana USER. Se quiserem esse diagnóstico alternativo, sua mudança de escopo deve ser explicitamente autorizada antes do uso; não confundir isso com autorização para mudar credenciais/permissões ou publicar reparo.

**Pergunta à origem:** consegue obter o detalhe da imagem rejeitada deste AD01 no Ads Manager/suporte Meta, preservando o anúncio e sem editar/reativar? Alternativamente, deseja submeter autorização explícita para a rota GET da própria Page, sem alterar as credenciais ativas?

## Continuidade sem replay

1. Manter campaign `120251246081230629` PAUSED; não forçar AD01 ACTIVE. Mesmo adset `120251246081300629`, 3 finais e 3 seeds; USD3500 e início `2026-11-15T00:26:40-05:00` preservados.
2. Após identificar causalmente a dependência, retomar ESTA manutenção para projetar o menor reparo no MESMO AD01; contrato request-scoped, backup/CAS, harness offline, negativos e regressões exigidos se código for necessário. Novo creative/image somente se indispensável e com prova/contrato autorizado; produção somente pelo owner. Não há autorização implícita nesta entrega.
3. Owner aplica somente esse reparo aprovado sob pai PAUSED, reconcilia resultado incerto por GET antes de retry, exige ausência real de issues e todos os estados/linhagem exatos. Sem repetir Engine/prepare/uploads/PBIA/reservas/naming e sem editar journal/manifest/registry/grants antigos.
4. Somente então, mantendo original digest `7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba` e OK `1571376388437577861`, usar os comandos abaixo. **Não executar agora**; o bloqueio AD01 continua aberto. O grant original também deve estar vigente; não renovar/sobrescrever aprovação para passar gate.

```
python3 /root/mgs-agent/scripts/ares-eggbev-target-clone.py recover-media --input /root/mgs-agent/data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937/request.json --approved-digest 7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba --approval-message-id 1571376388437577861
python3 /root/mgs-agent/scripts/ares-eggbev-target-clone.py finalize --input /root/mgs-agent/data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937/request.json --approved-digest 7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba --approval-message-id 1571376388437577861
```

## Preservação e testes

- Runner e módulo de recuperação sem alteração; 180 hashes runtime e 138 arquivos protegidos validados. Dos24 pins prévios, apenas os2 caminhos da referência Zeus/mirror mudaram intencionalmente para registrar o aprendizado.
- Não foi rodada nova regressão637/13suítes pois não houve alteração de código de produção; resultados anteriores permanecem históricos, não são apresentados como novo teste.
- Os3 probes GET foram exercitados de verdade. AST verificada sem chamada aos writers; nove imagens e a limitação code10/permissiongranted validadas por código.
- O primeiro verificador local rejeitou comparação textual da fonte por URL nativa rotativa. Corrigido para consumir a prova canônica de equivalência de bytes já gerada; nenhum gate de produção/GET foi mudado.
- Zero Meta/Drive writes, zero Engine/ativação/finalização, nenhum fork/processo background. Receipt/final/activation-intent continuam ausentes; lease RECOVERY_PENDING pertence ao mesmo request.
- Aprendizado salvo somente no perfil Zeus e seu mirror, referência `target-derived-media-reconciliation.md`; Ares não foi editado.
