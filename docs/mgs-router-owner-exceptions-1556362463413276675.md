# MGS Router — exceções do proprietário e atualização do painel

## Autoridade e supersessão ativa

Thread `1555381168894115912`. Decisões de Rodolfo:
- `1556362463413276675`: retirar rotas para `es.conectageral.com` e `es.portalrelevante.com`, que foram aposentados, e substituir somente os treze destinos comprovados de `job.conectageral.com/artigosjobs`.
- `1556362857359081503`: retirar o logout automático por tempo/inatividade.
- `1556366276501176494`: retirar `emprego.dicasfinancas.info` do Router.
- `1556366342972510238`: acrescentar o botão de exclusão de grupos.

Esta decisão **supersede a fidelidade literal integral** de `MGS-ROUTER-ELEVEN-DNS-ACTIVE-1556329456463908905` apenas para os conjuntos acima. A origem Keitaro permanece snapshot histórico; não reimportar os itens aposentados nem restaurar URLs/grupos antigos por comparação cega com a fonte. Fora dessas exceções, contratos de redirects, pesos e parâmetros continuam iguais. Os 35 DNS do cutover anterior e seus parâmetros/SSL não receberam escrita nesta tarefa. O DNS de `emprego.dicasfinancas.info` não foi excluído: a retirada autorizada ocorreu no Router, não no Cloudflare ou WordPress.

## 1. Rotas para os dois destinos espanhóis aposentados

Os nomes `es.*` eram **destinos**, não hosts públicos do Router. Todas as quinze opções de cada um dos dois aliases levavam exclusivamente a esses destinos:
- `tarjeta.conectageral.com/tarjetaescg`;
- `tarjeta.portalrelevante.com/tarjetaespr`.

As duas rotas foram excluídas por API, com snapshot/rollback e readback exato. GET/HEAD agora devolvem 404 nesses aliases. Outros caminhos dos dois hosts públicos e as trinta entradas históricas do catálogo foram preservados; não houve autorização para apagar o restante dos hosts ou reativar os sites espanhóis.

## 2. Treze destinos atuais de empregos

A rota pública `job.conectageral.com/artigosjobs` continua com os mesmos treze IDs, ordem, pesos relativos, modo Keitaro e UTMs originais. Mudaram somente as URLs correspondentes, do caminho `/en/<slug>/` em `conectageral.com` para o mesmo slug publicado em `jobs.conectageral.com`. As treze URLs de catálogo correspondentes foram sincronizadas; esses IDs eram usados exclusivamente nesta rota.

- Todas as treze páginas atuais devolveram HTTP200 com a query original preservada.
- As treze escolhas ponderadas foram efetivamente observadas em redirects públicos GET/HEAD.
- Soma bruta dos pesos:100; a configuração não foi normalizada ou redistribuída.
- Mapeamento exato e receipt: `data/mgs-router-destination-fix-1556362463413276675.json`.
- Outros 91 destinos404 sem equivalência comprovada não foram substituídos nesta entrega.

## 3. Retirada integral do host de empregos DicasFinancas

- Excluídas as **22 rotas** de `emprego.dicasfinancas.info`; todos os aliases responderam404 em GET/HEAD.
- Grupo `DICASFINANCAS PT` removido porque ficou realmente vazio, sem outros membros de rota ou catálogo.
- Os **26 IDs de destino são compartilhados por outros hosts**, inclusive `tarjeta.openzed.com`; todos foram preservados. O catálogo continua com943 entradas.
- O host não estava no cadastro explícito `domains.json`: era registrado pelas próprias rotas. Depois da retirada, desapareceu da lista pública de domínios do painel.
- Removido somente o check de verificação persistido desse host, preservando os demais. Sem isso `newApp` recusa a inicialização por referência a host não registrado.
- Snapshot privado final: `/root/.local/share/mgs-router-rollbacks/1556366276501176494-retry1/`. O primeiro preflight foi preservado no diretório sem sufixo; falhou **antes de qualquer escrita externa** devido ao check órfão no candidato. Causa corrigida, ambos os binários exercitados com estado completo e operação repetida com sucesso.

## 4. Sessões sem logout automático

O código anterior tinha um prazo fixo de **oito horas**, não um contador de inatividade: `Session.Expires` e cookie `Max-Age=28800`. Ambos foram removidos, junto da limpeza por deadline no login.

Preservados: lookup de token registrado/hasheado, Secure, HttpOnly, SameSite=Strict, CSRF, controle de origem, throttling e revogação pelo botão **Sair**. Uma nova sessão/login de outro usuário não cancela sessões existentes.

Limites explícitos: o cookie é de sessão, sem prazo automático. Fechar a sessão do navegador, usar Sair ou reiniciar o serviço ainda pode exigir login; as sessões do servidor continuam em memória. O deploy reiniciou somente `mgs-router.service`, uma vez, portanto os logins anteriores à publicação precisam de nova autenticação. Não foram alterados usuários/senhas, unidade, SSL, firewall ou gateways.

## 5. Grupos → Excluir grupo

Botão disponível em cada linha da aba Grupos. A confirmação informa quantas rotas e destinos ficarão **sem grupo**. A operação remove somente a organização e seus vínculos, **não** os links, URLs, destinos, pesos ou rotas. Salva tudo atomicamente na revisão da configuração; conflito exige reload, nunca sobrescreve uma alteração concorrente.

Chromium local testou cancelar, confirmar em grupo com duas rotas/um destino compartilhado, grupo vazio, filtros, reload e conflito de revisão. O teste Go mantém os dois destinos ponderados30/70 e exige zero grupos/vínculos depois da exclusão. O navegador público apenas abriu/cancelou a confirmação; nenhum grupo real foi excluído por um teste.

## Evidência final e estado atual

- **445 rotas**,943 destinos,29 grupos,19 hosts verificados no painel.
- **58 casos Go** aprovados, race detector, vet, build e Chromium local.
- **1.856 verificações públicas**: todas as445 rotas GET/HEAD com/sem query mais76 checks de caminhos reservados em19 hosts, sem divergência. O HTTP500 herdado da campanha304 continua explicitamente preservado.
- **48 verificações de retirada**: GET/HEAD nos22 aliases do host retirado e nos dois aliases espanhóis, todos404.
- Contas Rodolfo e Geizian validadas no navegador público: contagens,19 verdes/reload, treze URLs/pesos de empregos, botão/cancelamento de exclusão, zero escrita de UI/erroJS, mobile sem overflow.
- Cookie real sem deadline nas duas contas; reload mantém autenticação. Relógio JavaScript do navegador avançado nove horas, API de sessão continuou200; esse teste não simula nove horas do relógio do servidor. A ausência de prazo backend é coberta pelo código/teste de token registrado sem campo de deadline. Logout explícito continua revogando o token/retornando401.
- Fonte final: `data/mgs-router-authorized-panel-final-validation.json`; deploy: `data/mgs-router-panel-retirement-deploy-1556366276501176494.json`.
- Alterações de nomes/grupos feitas concorrentemente no painel foram preservadas pela leitura da revisão atual; não foram revertidas para labels do snapshot Keitaro.
- Procedimento reutilizável salvo em `mgs-router-operations/references/dns-cutover-and-group-edit.md`.
