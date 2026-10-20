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

Rodolfo confirmou este catálogo corporativo como escopo autorizado na mensagem acima. O registro de origem do snapshot foi produzido por leitura administrativa corporativa; isso é proveniência histórica, não instrução para Ares consultar catálogos globais. Contas obtidas pelo cadastro autorizado da BM Digital Trust. Registro executável: `data/ares/asset-scope.json`. O catálogo de publishers usado pelo Ares é `data/ares/sb-publisher-scope.json`, validado contra os hosts desta fonte; a rota `/company` do helper Ares é projeção local, sem HTTP global.

## Fontes operacionais de relatórios

- Contas, gasto, cobranças e faturas: `meta-ads-account-visualization/references/scoped-generic-reporting.md` e `scripts/ares-scoped-report.py`. O catálogo positivo define a seleção inclusive em pedidos genéricos; campos/contas não expostos pela credencial ficam indisponíveis, sem buscar outro portfólio, perfil de agente ou credencial administrativa.
- Faturas: somente leitura do edge da BM operacional, com contas relacionadas comprovadas no cadastro; nunca consultar BM ou fatura desconhecida por ID como fallback. Gasto e cartão atual não comprovam fatura nem cartão efetivamente cobrado.
- Receita por domínio: publishers resolvidos da projeção local e validados antes do relatório SB. Não obter catálogo remoto global para filtrar depois.
- Evidências de referência do Ares: `data/ares/`, `reports/ares/` e fontes canônicas específicas apontadas pelo mapa. Inventários, históricos, logs e backups globais compartilhados não são fontes alternativas para relatórios do Ares. Não apagar ou alterar dados de outras operações para corrigir o roteamento do Ares.
- Servidor, identidade do serviço, cofre, restart e revogação de permissões não pertencem a este pedido, conforme correção expressa de Rodolfo nesta thread; nenhuma proposta desse tipo fica como condição de aceite do recorte operacional.


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
