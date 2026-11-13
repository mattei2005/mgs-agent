# ClouDNS — acesso operacional MGS

Status: acesso API autenticado e leitura validada em 2026-11-13. Dono: Rodolfo Mattei; executor: Zeus.

## Autoridade e limites

- Thread de origem: `1570829578987905088`.
- Rodolfo escolheu API users (acesso completo da credencial) na mensagem `1570833701430894685` e confirmou o armazenamento no 1Password em `1570860268597158018`.
- Capacidade técnica full-account não significa autorização automática para alterar DNS, permissões, credenciais, billing ou outros serviços. Aplicar os gates canônicos de AGENT.md por operação.
- Escopo efetivamente exercitado: autenticação, IP observado pelo provedor e leitura dos registros/SOA de `scorexboost.com`; nenhum teste de escrita foi executado.

## Rota de credencial

- Fonte única: 1Password, cofre `MGS Conteúdo`, item `www.cloudns.net`, conta `support@matteiservicesinc.com`.
- Usar os campos exatos `auth-id` e `auth-password`; não confundir auth-password com a senha do login web. Campos auxiliares: `ip` e `url`.
- Resolver via `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`; se um ID antigo não existir, redescobrir por cofre, título, username e presença dos campos de API. Não usar o item homônimo de outro cofre por ordem da lista.
- Nunca copiar valores da credencial para este documento, registry, skill, logs ou Discord.
- Endpoint oficial fixo: `https://api.cloudns.net/`. Enviar autenticação por corpo HTTPS POST, nunca query string ou argumentos de processo.

## Transporte validado

- Allowlist de saída IPv4: `2.25.165.171`, confirmada pelo próprio endpoint `ip/get-my-ip.json` após login bem-sucedido.
- O caminho IPv6 tentou `2a02:4780:75:4061::1` e foi recusado pela allowlist. Usar IPv4 somente no cliente dessa integração, sem alterar rede global, allowlist ou credencial.
- A presença de IPv6 no host não exige ampliar a permissão IP. Revalidar o IP no provedor quando mudar o ambiente executor.

## Zona e exportação

- Zona: `scorexboost.com`; painel informado pelo CEO: `https://www.cloudns.net/records-geodns/domain/14802160/`.
- `jobs.scorexboost.com` pertence à mesma zona.
- Leitura validada: 13 registros gerenciados (4 A, 4 NS, 2 TXT, 2 CNAME, 1 AAAA), além dos detalhes SOA consultados separadamente. Isso é uma observação, não contagem permanente.
- A API `dns/records.json` retornou os campos GeoDNS; preservar `geodns-location`, código/nome, status e demais campos. A documentação de listagem contém nota genérica de master zones, mas a resposta real desta zona GeoDNS foi obtida e comparada por leitura independente.
- `dns/records-export.json` em BIND não suporta GeoDNS segundo a documentação. O TXT entregue é um inventário textual integral, não arquivo BIND importável.
- Receita desta execução: `/root/.hermes/profiles/zeus/cache/scratch/cloudns-scorexboost-export/receipt.json` (cache temporário; não é fonte durável).
- Procedimento reutilizável: skill `cloudns-api-operations`.

## Documentação oficial

- Autenticação: https://www.cloudns.net/wiki/article/42/
- Teste de login: https://www.cloudns.net/wiki/article/45/
- IP observado: https://www.cloudns.net/wiki/article/307/
- Listagem de registros: https://www.cloudns.net/wiki/article/57/
- SOA: https://www.cloudns.net/wiki/article/62/
- Limitação BIND/GeoDNS: https://www.cloudns.net/wiki/article/166/
