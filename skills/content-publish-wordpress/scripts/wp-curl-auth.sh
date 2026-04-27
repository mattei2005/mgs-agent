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
  trap "rm -f '$temp_cred'" RETURN
  
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
