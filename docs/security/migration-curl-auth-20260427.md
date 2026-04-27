# Migration: WP Scripts → wp_curl_auth helper

**Data:** 27/04/2026
**Tipo:** Security hardening
**Severidade:** Medium (credenciais expostas em ps aux)

## Problema

Scripts WordPress passavam credenciais inline via `curl -u "$user:$pass"`.
Isso expunha senhas em:
- Process listings (`ps aux`, `/proc/*/cmdline`)
- Bash history (caso execute interativamente)
- Logs de sistema (caso script falhasse com argv visível)

Documentado em CLAUDE.md (linha 210): "Acceptable for now; future fix = curl -K config-file".

## Solução

Helper `wp-curl-auth.sh` criado em `/root/mgs-agent/skills/content-publish-wordpress/scripts/`.

Funcionamento:
1. Recebe user + pass como argumentos da função (locais ao escopo, não argv do curl)
2. Cria tempfile via `mktemp` com `chmod 600` (apenas root lê)
3. Escreve credenciais no formato `user = "u:p"` no tempfile
4. Executa `curl -K $tempfile $@` (curl lê creds do arquivo, não da linha de comando)
5. `trap RETURN` + `rm -f` explícito para limpeza imediata

Garantia: senha NUNCA aparece em `ps aux` ou `/proc/$PID/cmdline`.

## Scripts migrados

| Script | Ocorrências | Commit |
|--------|-------------|--------|
| upload-image.sh | 1 | bc9bfb3 |
| create-post.sh | 1 | 06885b3 |
| resolve-term.sh | 2 | 317c416 |
| update-yoast.sh | 3 | 7ac78da |

**Total: 7 ocorrências em 4 scripts.**

## Validação

- `upload-image.sh` testado em produção (eggbev.com): HTTP 2xx + delete cleanup OK
- `bash -n` em todos os 5 scripts: sintaxe OK
- `grep -rn "curl.*-u"` retorna ZERO ocorrências nos scripts WP

## Backup

Versões originais preservadas em:
`/root/mgs-agent/data/scripts-backup-pre-curl-auth-20260427-131820/`

Pode ser deletado após 1 semana de validação em produção.

## Referências

- curl docs: https://curl.se/docs/manpage.html#-K
- CIS Benchmark Linux 5.4.5: "Limit access to credential files"
