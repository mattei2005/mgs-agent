# MGS Router — versão inicial publicada

## Estado

Publicado em https://route.mgsdigitalcorp.com/login, com contas individuais `rodolfo` e `geizian`, após confirmação crítica `1555623974673842279`. Login, UI pública e logout validados para ambos. Estado canônico em `docs/mgs-router-public-deployment.md`, receipt em `data/mgs-router-deployment.json` e prova em `data/mgs-router-public-validation.json`. Sem rotas reais cadastradas ou alterações em DTR/SB.

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

## Implantação confirmada

- Cloudflare: um único A `route.mgsdigitalcorp.com` → `2.25.165.171`, proxied=true, ttl=1 (Auto), readback confirmado. SSL da zona full mantido.
- Contas: `rodolfo` e `geizian` gerenciam rotas; sem acesso adicional à VPS, Cloudflare ou agentes. Senhas individuais nos itens `MGS Router - Rodolfo` e `MGS Router - Geizian` do 1Password.
- Serviço público: `mgs-router.service`, usuário não-root, TLS de origem e peers restritos à Cloudflare, CPUQuota=50% de um core e MemoryMax=256M. Origem direta403, API anônima401 e HTTPS público200 validados. Mudanças futuras em `/etc` ou credenciais exigem os gates próprios, não reutilizar a confirmação inicial.
- Nenhuma alteração no DTR/SB ou nos subdomínios de tráfego Wantabrand nesta etapa.

## Limitações

- O endpoint de salvar aplica o conjunto completo de rotas, com proteção de revisão; a interface só oferece cadastro e edição de destino, não exclusão.
- Sessões expiram em oito horas e são invalidadas em restart; não há recuperação de senha nem cadastro público.
- Distribuição ponderada, geofiltros e outros comportamentos não foram implementados.
- Testes locais não provam capacidade de produção nem proteção contra DDoS da VPS compartilhada.
