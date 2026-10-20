#!/usr/bin/env bash
set -euo pipefail
# Execute only when you decide to create a PRIVATE repository in your authenticated GitHub account.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:-android-link-cosmic}"
[[ "$NAME" =~ ^[a-zA-Z0-9._-]+$ ]] || { echo 'Nome de repositório inválido.' >&2; exit 1; }
command -v gh >/dev/null || { echo 'GitHub CLI ausente. Instale gh e execute gh auth login.' >&2; exit 1; }
command -v git >/dev/null || { echo 'git ausente.' >&2; exit 1; }
if ! gh auth status >/dev/null 2>&1; then
  echo 'Autentique: gh auth login' >&2
  exit 1
fi
OWNER="$(gh api user --jq .login)"
[[ -n "$OWNER" ]] || { echo 'Não foi possível determinar o usuário autenticado.' >&2; exit 1; }
if gh repo view "$OWNER/$NAME" >/dev/null 2>&1; then
  echo "Repositório já existe: https://github.com/$OWNER/$NAME" >&2
  echo 'Por segurança, o script não modifica repositórios preexistentes.' >&2
  exit 1
fi
cd "$ROOT"
if [[ ! -d .git ]]; then
  git init -b main
fi
if git remote get-url origin >/dev/null 2>&1; then
  echo 'Já existe remote origin; revise-o manualmente antes de publicar.' >&2
  exit 1
fi
git add --all
if ! git diff --cached --quiet; then
  git commit -m "feat: Android Link GTK4 with Wi-Fi webcam and battery monitoring"
fi
if [[ -z "$(git log -1 --format=%H 2>/dev/null || true)" ]]; then
  echo 'Nenhum commit inicial encontrado.' >&2
  exit 1
fi
# The only remote mutation: new private repository, requiring gh authentication.
gh repo create "$NAME" --private --source . --remote origin --push
printf '\nRepositório privado criado: https://github.com/%s/%s\n' "$OWNER" "$NAME"
