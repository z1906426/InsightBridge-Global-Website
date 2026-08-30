#!/bin/bash
# Deploy InsightBridge Global main site → Cloudflare Pages (direct upload)
# Project: insightbridge-global | Production branch: main | Domains: insightbridge.global
#
# Usage:
#   ./deploy-pages.sh                  # production deploy (goes live on insightbridge.global)
#   ./deploy-pages.sh --branch test    # preview deploy → https://test.insightbridge-global.pages.dev
#
# Auth (either):
#   1. CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID already exported in env
#   2. ~/.openclaw/credentials/cloudflare.json with key "api_token_pages" (OpenClaw host default)
#
# Layout (CF Pages Functions requirement — do not change):
#   frontend/functions/  → Pages Functions (project root; NOT inside site/)
#   frontend/site/       → static assets (deploy directory)
set -euo pipefail

CF_JSON="$HOME/.openclaw/credentials/cloudflare.json"
if [[ -z "${CLOUDFLARE_API_TOKEN:-}" && -f "$CF_JSON" ]]; then
  export CLOUDFLARE_API_TOKEN="$(python3 -c "import json;print(json.load(open('$CF_JSON'))['api_token_pages'])")"
fi
if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
  export CLOUDFLARE_ACCOUNT_ID="d1efc71478a9794a3e2ee88f6ed323cd"
fi
if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "ERROR: no CLOUDFLARE_API_TOKEN (env or $CF_JSON)" >&2
  exit 1
fi

cd "$(dirname "$0")"
echo "→ deploying frontend/site (+ functions) to Cloudflare Pages project insightbridge-global"
exec npx --yes wrangler pages deploy site --project-name=insightbridge-global "$@"
