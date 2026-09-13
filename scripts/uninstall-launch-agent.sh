#!/bin/zsh
set -eu

for component in agent worker; do
  label="pl.marketplace-listing-agent.$component"
  plist_path="$HOME/Library/LaunchAgents/$label.plist"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  rm -f "$plist_path"
  echo "Usunięto usługę $label."
done
echo "Dane aplikacji pozostawiono bez zmian."
