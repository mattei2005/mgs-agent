# Sites SFTP — fora do RunCloud

Conteúdo originalmente em skill `sftp-deployment` (arquivada 2026-05-06).

## Sites cobertos

| Domínio | Item 1Password | IP |
|---|---|---|
| openzed.com | `SFTP openzed servers` | 44.208.155.39 |
| finanzas.openzed.com | `SFTP finanzas.openzed servers` | 3.19.138.131 |
| cliquet.com | `SFTP cliquet servers` | 35.175.97.196 |
| finanzas.cliquet.com | `SFTP finanzas.cliquet servers` | 18.116.18.34 |

> **fincgriffin.com** — servidor externo sem SSH/SFTP conhecido, mas com acesso programático WordPress validado em 2026-08-17. Usar o item 1Password `Fincgriffin Wordpress`: `username` + `password` para WP Admin e `app user` + `app password` para REST. Instalação/ativação de plugins usa `/wp-json/wp/v2/plugins`; configuração usa login autenticado e POST real para `/wp-admin/options.php`, seguida de readback na página do plugin.

## Arquitetura (CRÍTICO)

- Instâncias **AWS EC2 com stack Bitnami WordPress** — NÃO RunCloud
- Webroot real: `/opt/bitnami/wordpress/`
- Usuário SFTP `wpfiles` conecta em `/opt/bitnami/wordpress/` como raiz
- **`wpfiles` é 100% READ-ONLY** — `put`, `mkdir`, `rename` → Permission denied em todos os diretórios
- Usuário com escrita = `bitnami` + chave `.pem` EC2
- SSH interativo bloqueado: `"This service allows sftp connections only."` para `wpfiles`

## Credenciais SFTP

```bash
HOST=$(op item get "SFTP openzed servers" --vault "MGS Conteúdo" --fields host --reveal)
PORT=$(op item get "SFTP openzed servers" --vault "MGS Conteúdo" --fields port --reveal)
PASS=$(op item get "SFTP openzed servers" --vault "MGS Conteúdo" --fields wpfiles --reveal)
# Campo username do item está VAZIO — ignorar. Usar "wpfiles" como username.
# A senha está no campo de label "wpfiles" (não "password").
```

## Verificação de conectividade

```bash
for IP in 44.208.155.39 3.19.138.131 35.175.97.196 18.116.18.34; do
  timeout 3 bash -c "echo > /dev/tcp/$IP/22" 2>/dev/null && echo "ABERTA: $IP" || echo "FECHADA: $IP"
done

# Listar raiz do WP via SFTP (confirma credenciais)
sshpass -p "$PASS" sftp -P 22 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs wpfiles@$HOST << 'EOF'
ls
ls wp-content
EOF
```

## Uso legítimo do SFTP (leitura/validação pós-deploy)

```bash
# Verificar arquivos em mu-plugins após deploy
sshpass -p "$PASS" sftp -P 22 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs wpfiles@$HOST << 'EOF'
ls wp-content/mu-plugins
EOF
# Nota: usar path RELATIVO (sem /). Path absoluto "/wp-content/..." retorna "File not found".
```

## Recuperação de site DOWN por snippet PHP inválido (Bitnami)

Se SFTP é read-only e REST API está em 500:
1. **Único caminho:** acesso MySQL direto
2. Via AWS Console ou bitnami SSH (porta 22, usuário `bitnami`, chave `.pem`)
3. Query de recovery:
   ```sql
   UPDATE <db>.wp_posts SET post_status='draft'
   WHERE post_type='wpcode' AND post_title='<snippet_title>';
   ```
4. Reiniciar Apache: `sudo /opt/bitnami/ctlscript.sh restart apache`

## Pitfalls

- **`wpfiles` é 100% read-only** — confirmado em 23/04/2026. Não há diretório com escrita.
- **SSH interativo bloqueado** para `wpfiles` — apenas SFTP funciona.
- **Path RELATIVO no SFTP** — `ls wp-content/mu-plugins/` funciona; `ls /wp-content/mu-plugins/` retorna "not found".
- **`mu-plugins` não existe por padrão** — criar via elFinder ou SSH bitnami antes do primeiro deploy.
- **Não usar `StrictHostKeyChecking` desativado**. Na primeira conexão, usar `StrictHostKeyChecking=accept-new` + `UserKnownHostsFile=/root/.ssh/known_hosts_mgs`.
- **Sessão WP Admin expira em ~5 min** nos servidores Bitnami.
- **WPCode snippet = alto risco** sem .pem (incidente real: openzed.com down 18h em 2026-04-25).
  Preferir sempre elFinder `cmd: put` — ver `references/bitnami-mu-plugin-deploy.md`.
