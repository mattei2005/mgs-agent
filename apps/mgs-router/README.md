# MGS Router — versão inicial local

## Estado

Implementação local de roteador e interface. Não está publicado em route.mgsdigitalcorp.com e não possui usuários de produção provisionados. DNS, certificado/chave, contas e serviço persistente aguardam confirmação dos gates aplicáveis.

## Escopo

- Rotas por domínio + caminho, destino HTTPS, redirect 302.
- Preservação da query recebida, incluindo duplicatas e percent-encoding.
- Interface PT-BR: adicionar rota, editar destino mantendo link público, filtro por domínio/pesquisa, copiar link e testar.
- Sem tracking, cliques, métricas comerciais, relatórios, postbacks ou licença Keitaro.
- Login local por usuário com PBKDF2-SHA256/600.000 iterações, sessões temporárias, cookies HttpOnly/Secure/SameSite Strict, CSRF + validação de origem, CSP sem inline/eval, limite de tentativas/concurrency de login.
- Gravação atômica de configuração, controle de revisão para edição concorrente, estado fora do Git.
- HTTP de teste somente em localhost; fora dele o binário exige certificado e chave TLS e allowlist oficial de IPs Cloudflare. Cabeçalho de IP do cliente só é confiado após validar o peer de origem.

## Código e dependências

Go stdlib sem módulos externos. Go instalado somente em `/root/.local/share/mgs-router-toolchain/go/`, fora de `/usr` e sem alterar o runtime dos agentes. QA Playwright isolado em `/root/.local/share/mgs-router-toolchain/qa-venv/`, reutilizando Chromium existente.

Comandos locais:

```
/root/.local/share/mgs-router-toolchain/go/bin/go test -v ./...
/root/.local/share/mgs-router-toolchain/go/bin/go test -race ./...
/root/.local/share/mgs-router-toolchain/go/bin/go vet ./...
node --check web/app.js
/root/.local/share/mgs-router-toolchain/go/bin/go build -trimpath -o /root/.local/share/mgs-router-toolchain/mgs-router .
```

Os testes de navegador criam apenas usuários e sessões sintéticos dentro de diretórios de teste. Não provisionam Rodolfo ou Geizian e não navegam para destinos de produção. Sem credenciais em output.

## Gates preparados

- Cloudflare: criar um único A `route.mgsdigitalcorp.com` → `2.25.165.171`, proxied=true, ttl=1 (Auto). Preflight encontrou o hostname sem registros na zona ativa mgsdigitalcorp.com através do token mattei20052. SSL da zona é full; não mudar a zona inteira.
- Contas propostas: usernames `rodolfo` e `geizian`, ambos gerenciam rotas; não recebem acesso à VPS, Cloudflare ou agentes. Gerar senhas individuais e guardar no 1Password após confirmação crítica.
- Exposição pública: certificado/chave e unidade systemd com limites CPU/memória e usuário de serviço dedicado exigem confirmação exata antes de gravar `/etc` ou criar credenciais. Ainda não executado.
- Nenhuma alteração no DTR/SB ou nos subdomínios de tráfego Wantabrand nesta etapa.

## Limitações

- O endpoint de salvar aplica o conjunto completo de rotas, com proteção de revisão; a interface só oferece cadastro e edição de destino, não exclusão.
- Sessões expiram em oito horas e são invalidadas em restart; não há recuperação de senha nem cadastro público.
- Distribuição ponderada, geofiltros e outros comportamentos não foram implementados.
- Testes locais não provam capacidade de produção nem proteção contra DDoS da VPS compartilhada.
