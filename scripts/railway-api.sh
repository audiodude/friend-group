#!/usr/bin/env bash
# Railway GraphQL API helper (fixed token path)
set -e

CONFIG_FILE="$HOME/.railway/config.json"
TOKEN=$(jq -r '.user.accessToken // .user.token' "$CONFIG_FILE")

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo '{"error": "No Railway token found. Run: railway login"}'
  exit 1
fi

if [[ -n "$2" ]]; then
  PAYLOAD=$(jq -n --arg q "$1" --argjson v "$2" '{query: $q, variables: $v}')
else
  PAYLOAD=$(jq -n --arg q "$1" '{query: $q}')
fi

curl -s https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
