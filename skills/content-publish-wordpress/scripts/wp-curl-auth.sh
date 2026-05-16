#!/bin/bash
# wp-curl-auth.sh — Helper para curl autenticado seguro (sem expor credenciais em argv)
#
# Uso:
#   source wp-curl-auth.sh
#   wp_curl_auth "$user" "$pass" [outros args do curl...]
#
# Exemplo:
#   wp_curl_auth "$user" "$pass" -X POST -H "Content-Type: application/json" \
#     -d "$payload" "$wp/wp-json/wp/v2/posts"
#
# A função cria arquivo temp 600 com credenciais, executa curl com -K, e limpa no final.
# Garantia: senha NUNCA aparece em ps aux ou /proc/*/cmdline.

wp_curl_auth() {
  local user="$1"
  local pass="$2"
  shift 2
  
  if [ -z "$user" ] || [ -z "$pass" ]; then
    echo "ERROR: wp_curl_auth requires user and pass" >&2
    return 1
  fi
  
  # Criar arquivo temp com permissão restrita
  local temp_cred
  temp_cred=$(mktemp)
  chmod 600 "$temp_cred"
  
  # Garantir limpeza mesmo em caso de erro
  trap 'rm -f "$temp_cred"' RETURN
  
  # Escrever credenciais em formato curl -K (config file)
  # Importante: aspas duplas + escape de caracteres especiais
  printf 'user = "%s:%s"\n' "$user" "$pass" > "$temp_cred"
  
  # Executar curl com -K (lê credenciais do arquivo)
  curl -K "$temp_cred" "$@"
  local exit_code=$?
  
  # Limpar imediatamente (trap RETURN também limpa, mas defesa em camadas)
  rm -f "$temp_cred"
  
  return $exit_code
}

# Permite testar standalone:
# wp_curl_auth user pass -sS https://example.com


# Executa request WP REST retornando SEMPRE um HTTP code único no stdout.
# Preserva o body de erro em $out via --fail-with-body, mas não deixa curl rc=22
# contaminar o caller com "404\n000". Falha de transporte sem HTTP vira 000.
# Uso:
#   http=$(wp_curl_auth_http "$tmp" "$user" "$pass" -H ... -X POST URL)
wp_curl_auth_http() {
  local out="$1"
  local user="$2"
  local pass="$3"
  shift 3

  local http rc
  set +e
  http=$(wp_curl_auth "$user" "$pass" \
    --fail-with-body \
    --connect-timeout "${WP_CURL_CONNECT_TIMEOUT:-15}" \
    --max-time "${WP_CURL_MAX_TIME:-90}" \
    --retry "${WP_CURL_RETRY:-2}" \
    --retry-delay "${WP_CURL_RETRY_DELAY:-1}" \
    --retry-connrefused \
    -sS -o "$out" -w '%{http_code}' "$@")
  rc=$?
  set -e

  if [[ "$http" =~ ^[0-9]{3}$ ]]; then
    printf '%s' "$http"
  elif [[ "$rc" -ne 0 ]]; then
    printf '000'
  else
    printf '%s' "${http:-000}"
  fi
  return 0
}
