#!/bin/sh
# Speichert Änderungen der Workflows (gerenderte Medien, Status, Zahlen) im Repository.
set -e
git config user.name "energyshield-bot"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then
  echo "Keine Änderungen."
  exit 0
fi
git commit -m "$1"
git pull --rebase
git push
