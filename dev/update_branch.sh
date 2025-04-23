#!/usr/bin/env bash
set -euo pipefail

# Usage: ./sync-with-main.sh [<remote>] [<main-branch>]
# Defaults: remote=origin, main-branch=main

REMOTE="${1:-origin}"
MAIN_BRANCH="${2:-main}"

# Figure out what branch we're on
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$CURRENT_BRANCH" == "$MAIN_BRANCH" ]]; then
  echo "⚠️  You are on '$MAIN_BRANCH' – please checkout your feature branch first."
  exit 1
fi

echo "🚀 Fetching latest from '$REMOTE'..."
git fetch "$REMOTE"

echo "🔄 Updating '$MAIN_BRANCH'..."
git checkout "$MAIN_BRANCH"
git pull "$REMOTE" "$MAIN_BRANCH"

echo "🔙 Switching back to '$CURRENT_BRANCH'..."
git checkout "$CURRENT_BRANCH"

echo "🧹 Resetting '$CURRENT_BRANCH' to match '$MAIN_BRANCH'..."
git reset --hard "$MAIN_BRANCH"

echo "✅ '$CURRENT_BRANCH' is now in sync with '$MAIN_BRANCH'."
