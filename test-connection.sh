#!/bin/bash

# Helper para curl autenticado seguro (não expõe senha em ps aux)
source "/root/mgs-agent/skills/content-publish-wordpress/scripts/wp-curl-auth.sh"

SITE="eggbev"
USERNAME="raqueloliveira"
APP_PASSWORD=$(op item get "eggbev - WordPress" --vault "MGS Conteúdo" --fields wp_app_password --reveal)
WP_URL="https://eggbev.com/wp-json/wp/v2"

echo "🧪 Testando conexão com $SITE..."
echo "📍 URL: $WP_URL"
echo "👤 User: $USERNAME"
echo ""

echo "→ Teste 1: API pública"
curl -s -o /dev/null -w "   Status: %{http_code}\n" "$WP_URL"

echo "→ Teste 2: Autenticação"
RESPONSE=$(wp_curl_auth "$USERNAME" "$APP_PASSWORD" -s -w "\n%{http_code}" "$WP_URL/users/me")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
  USER_NAME=$(echo "$BODY" | grep -oP '"name":"[^"]*' | head -1 | sed 's/"name":"//')
  USER_ID=$(echo "$BODY" | grep -oP '"id":\K[0-9]+' | head -1)
  echo "   ✅ Autenticado como: $USER_NAME (ID: $USER_ID)"
else
  echo "   ❌ Falha. HTTP $HTTP_CODE"
  echo "   Body: $BODY"
fi

echo "→ Teste 3: Listar categorias"
CATEGORIES=$(wp_curl_auth "$USERNAME" "$APP_PASSWORD" -s "$WP_URL/categories?per_page=5")
COUNT=$(echo "$CATEGORIES" | grep -oP '"id":' | wc -l)
echo "   Encontrou $COUNT categorias"


echo ""
echo "🎯 Teste concluído"
