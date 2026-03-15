#!/usr/bin/env bash
# Setup org-level webhook for NeoTubeX
# This replaces per-repo webhooks — all pushes go to deploy.sorevo.de
#
# Prerequisites:
#   - gh CLI authenticated with admin:org_hook scope
#   - Run: gh auth refresh -h github.com -s admin:org_hook
#
# Usage: bash scripts/setup-org-webhook.sh [webhook-secret]

set -euo pipefail

ORG="NeoTubeX"
WEBHOOK_URL="https://deploy.sorevo.de/webhook/github"
SECRET="${1:-}"

echo "Setting up org-level webhook for $ORG -> $WEBHOOK_URL"

# Check if webhook already exists
EXISTING=$(gh api "orgs/$ORG/hooks" --jq '.[].config.url' 2>/dev/null || echo "")
if echo "$EXISTING" | grep -q "$WEBHOOK_URL"; then
    echo "Webhook already exists. Updating..."
    HOOK_ID=$(gh api "orgs/$ORG/hooks" --jq ".[] | select(.config.url==\"$WEBHOOK_URL\") | .id")
    if [ -n "$SECRET" ]; then
        gh api "orgs/$ORG/hooks/$HOOK_ID" --method PATCH \
            -f "config[url]=$WEBHOOK_URL" \
            -f "config[content_type]=json" \
            -f "config[secret]=$SECRET" \
            -F "active=true"
    else
        gh api "orgs/$ORG/hooks/$HOOK_ID" --method PATCH \
            -F "active=true"
    fi
    echo "Updated webhook (ID: $HOOK_ID)"
else
    echo "Creating new webhook..."
    ARGS=(
        "orgs/$ORG/hooks"
        --method POST
        -f "name=web"
        -f "config[url]=$WEBHOOK_URL"
        -f "config[content_type]=json"
        -f "events[]=push"
        -F "active=true"
    )
    if [ -n "$SECRET" ]; then
        ARGS+=(-f "config[secret]=$SECRET")
    fi
    RESULT=$(gh api "${ARGS[@]}" --jq '.id')
    echo "Created webhook (ID: $RESULT)"
fi

echo ""
echo "Done! All repos in $ORG will now trigger auto-deploy."
echo "You can remove per-repo webhooks with:"
echo "  gh api repos/$ORG/{repo}/hooks --jq '.[].id' | xargs -I{} gh api repos/$ORG/{repo}/hooks/{} --method DELETE"
