#!/usr/bin/env bash

# --- CONFIG ---
CONFIG_FILE=".wrkbranch"
ENV_VAR_NAME="WORKING_BRANCH"

# --- LOAD existing config if present ---
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"    # expects: export WORKING_BRANCH=branch-name
fi

# --- HANDLE override via first argument ---
if [ -n "$1" ]; then
  BRANCH="$1"
  echo "export $ENV_VAR_NAME=$BRANCH" > "$CONFIG_FILE"
  echo "🔧 Updated stored branch to '$BRANCH'"
  WORKING_BRANCH="$BRANCH"
fi

# --- ASK if still unset ---
if [ -z "${WORKING_BRANCH:-}" ]; then
  read -r -p "Enter your working branch name: " BRANCH
  echo "export $ENV_VAR_NAME=$BRANCH" > "$CONFIG_FILE"
  WORKING_BRANCH="$BRANCH"
  echo "💾 Saved '$BRANCH' as your working branch"
fi

# --- FETCH remote ---
echo "⏳ Fetching origin..."
git fetch origin

# --- CHECKOUT or CREATE branch ---
if git show-ref --verify --quiet "refs/heads/$WORKING_BRANCH"; then
  echo "✅ Checking out existing local branch '$WORKING_BRANCH'"
  git checkout "$WORKING_BRANCH"

elif git ls-remote --exit-code --heads origin "$WORKING_BRANCH" &>/dev/null; then
  echo "✅ Checking out remote branch 'origin/$WORKING_BRANCH'"
  git checkout --track "origin/$WORKING_BRANCH"

else
  echo "✨ Creating new branch '$WORKING_BRANCH' from origin/main"
  git checkout -b "$WORKING_BRANCH" origin/main
fi

# --- NON-INTERACTIVE REBASE with auto-stash ---
echo "🚀 Rebasing '$WORKING_BRANCH' onto origin/main (auto-stash)"
git rebase --autostash origin/main && \
  echo "✔️ Rebase complete"
