# Meta Ads Library — continuidade da sessão pela rota residencial

## Quando usar

Use quando uma coleta anterior da Meta Ads Library funcionou por `windows-home-socks` e uma execução posterior precisa reutilizar o mesmo perfil autenticado.

## Evidência operacional observada

Uma coleta autenticada pela rota residencial retornou:

```text
proxyMode                 windows-home-socks
resultText                ~63 results
Library IDs               42
Mídias detectadas         3 IMG + 30 VID
Cookies autenticados      c_user + xs presentes
Downloads piloto          3, HTTP 200
```

Após o túnel residencial ser encerrado, uma tentativa com o mesmo perfil por `direct-vps` mostrou zero resultados e o readback posterior já não continha `c_user`/`xs`. A conclusão durável não é que a sessão persistente falhou: a rota de rede mudou antes da reutilização.

## Procedimento seguro

1. Leia o `report.json` do último sucesso antes de abrir Chromium.
2. Se `proxyMode=windows-home-socks`, teste somente se `127.0.0.1:1080` está aceitando conexão.
3. Se a porta estiver fechada, não inicie o coletor nem o navegador de login pela VPS direta. Peça para reabrir o mesmo túnel residencial e mantê-lo aberto.
4. Execute com:

```bash
HERA_META_LIBRARY_PROXY=socks5://127.0.0.1:1080 \
  /root/mgs-agent/scripts/hera-meta-library-collector.sh \
  --url '<META_LIBRARY_URL>' --download 100 --scrolls 100
```

5. Faça readback apenas dos nomes/contagens de cookies; nunca exponha valores. Confirme `c_user` e `xs` antes de declarar sessão autenticada.
6. Só considere a coleta completa após quatro ciclos estáveis sem novos IDs/mídias, downloads HTTP 200 válidos e relatório/screenshot reais.

## Pitfalls

- Não interpretar `profileReused=true` como autenticação; valide `authenticatedLikely` e os nomes `c_user`/`xs`.
- Não usar uma execução direta como “teste rápido” quando o último sucesso dependia do SOCKS residencial.
- Não confundir `~63 results` com 63 assets únicos: deduplicar por URL/hash e registrar Library IDs separadamente.
- `captcha=true` pode ser falso positivo por texto escondido no HTML; dê prioridade ao DOM visível, IDs, mídia e screenshot.
