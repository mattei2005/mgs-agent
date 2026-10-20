# Ares — escopo operacional de ativos MGS

Status: canônico ativo. Autoridade: Rodolfo Mattei, mensagem `1562127427151339701`, thread `1562104297926295623`.

## Limite e precedência

A operação MGS do Ares é exclusivamente sobre contas de anúncio da BM Digital Trust (`155263197283282`) e hosts corporativos cadastrados no catálogo Smart Bidding das companies `digital-trust` e `digital-trust-2`. O catálogo inclui publishers cadastrados, ativos ou inativos; acesso de usuário mais estreito não redefine o catálogo corporativo. Esta regra supersede para Ares o escopo geral baseado apenas no cadastro institucional de sites; Atena não muda.

O app `minibot` (`1299247318762949`) permanece autorizado como dependência técnica, inclusive quando seu proprietário é outro portfólio. Ownership, aprovação, credencial ou capacidade técnica desse app não autorizam leitura/operação de contas, sites ou inventários do portfólio proprietário. Não revogar app, tokens ou permissões Meta neste cutover.

## Gate obrigatório anterior à ferramenta

- Conta de anúncio: `python3 /root/mgs-agent/scripts/mgs-ares-asset-scope.py check-account <ID-ou-act_ID> --json`; exigir allowed=true antes de qualquer consulta de campanhas, gasto, billing, permissões ou write.
- Domínio/URL: `python3 /root/mgs-agent/scripts/mgs-domain-scope.py check --agent ares <host-ou-URL>`; correspondência exata, www somente como alias e nenhum subdomínio implícito.
- Pedido global de Meta/SB não supera esse limite. Listar somente cadastros positivos locais aprovados; não enumerar outros portfólios ou provedores globais. Operação mista processa somente alvos permitidos, sem eco dos demais.
- IDs não cadastrados falham fechado. Atualização do snapshot exige readback da BM/SB pelo Zeus e a autoridade vigente; nunca inferir inclusão pelo nome ou pelo proprietário do app.

## Fonte afirmativa e snapshot

Rodolfo confirmou este catálogo corporativo como escopo autorizado na mensagem acima. Snapshot ao vivo GET /company por sessão administrativa; propriedade e escopo afirmados por essa decisão, não inferidos de mera hospedagem/receita. Contas obtidas pela edge paginada owned_ad_accounts da BM Digital Trust. Registro executável: `data/ares/asset-scope.json`.

Hosts corporativos autorizados ao Ares neste snapshot:

- `autocreditadx.com`
- `boostingecon.com`
- `carcreditad.com`
- `cephyric.com`
- `cliquet.com`
- `conectageral.com`
- `creditoparaveiculo.com`
- `de.newsoun.com`
- `dicasfinancas.info`
- `ducapes.com`
- `eggbev.com`
- `empleo.seuprimeiroempregoam.com`
- `escalatepower.com`
- `finance.ducapes.com`
- `finance.topfeed.fun`
- `finance.wantabrand.com`
- `financeadx.com`
- `financiamentoautoadx.com`
- `financiarveiculo.com`
- `finanzas.cliquet.com`
- `finanzas.conectageral.com`
- `finanzas.eggbev.com`
- `finanzas.lyzmo.com`
- `finanzas.newsoun.com`
- `finanzas.openzed.com`
- `finanzas.portalrelevante.com`
- `finanzas.topfeed.fun`
- `finanzas.wavesbee.com`
- `finanzas.zuout.com`
- `finanzas.zytiva.com`
- `fincgriffin.com`
- `gamezonead.com`
- `gamingadx.com`
- `growpowerhub.com`
- `helixenit.net`
- `infinitynexx.com`
- `jobscana.com`
- `lyzmo.com`
- `marevelx.com`
- `mavroa.com`
- `newsoun.com`
- `openzed.com`
- `portalrelevante.com`
- `seuprimeiroempregoam.com`
- `topfeed.fun`
- `vizioid.com`
- `wavesbee.com`
- `xyvlov.com`
- `yolokfx.com`
- `zuout.com`
- `zyclor.com`
- `zytiva.com`
