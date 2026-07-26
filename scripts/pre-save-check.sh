#!/bin/bash
# /app/scripts/pre-save-check.sh
#
# Manual "Pull-before-Save" helper — implements Rule #1 from PRD.md.
# Run this before clicking "Save to GitHub" in the Emergent UI, or invoke it
# from an agent right before proposing that the user re-publish.
#
# Behavior:
#   - Fetches origin/main
#   - If pod is behind, fast-forwards
#   - If diverged, prints instructions and exits 1
#   - Prints the current HEAD and a short summary so agent can log it

set -e
cd "$(dirname "$0")/.."

if ! git remote get-url origin >/dev/null 2>&1; then
    echo "[pre-save] restoring missing 'origin' remote ..."
    git remote add origin https://github.com/z1906426/InsightBridge-Global-Website.git
fi

echo "[pre-save] fetching origin/main ..."
git fetch origin main --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
BASE=$(git merge-base HEAD origin/main 2>/dev/null || echo "")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[pre-save] SYNCED — pod HEAD == origin/main ($LOCAL)"
    exit 0
fi

if [ "$BASE" = "$REMOTE" ]; then
    echo "[pre-save] LOCAL AHEAD by $(git rev-list --count origin/main..HEAD) commits — Save to GitHub will push cleanly."
    exit 0
fi

if [ "$BASE" = "$LOCAL" ]; then
    BEHIND=$(git rev-list --count HEAD..origin/main)
    echo "[pre-save] REMOTE AHEAD by $BEHIND commits — fast-forwarding pod ..."
    git reset --hard origin/main
    echo "[pre-save] pod is now at $(git rev-parse HEAD). Restart supervisor if needed."
    exit 0
fi

echo "[pre-save] DIVERGED — manual review required. See /app/.git/hooks/pre-push for reset command."
exit 1
