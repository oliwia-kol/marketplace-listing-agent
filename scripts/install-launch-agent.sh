#!/bin/zsh
set -eu

app_dir="${MARKETPLACE_AGENT_APP_DIR:-$HOME/Library/Application Support/Marketplace Listing Agent}"
script_dir="${0:A:h}"
executable="${MARKETPLACE_AGENT_EXECUTABLE:-$(command -v marketplace-listing-agent || true)}"
if [[ -z "$executable" && -x "$script_dir/../.venv/bin/marketplace-listing-agent" ]]; then
  executable="$script_dir/../.venv/bin/marketplace-listing-agent"
fi
if [[ -z "$executable" ]]; then
  echo "Nie znaleziono marketplace-listing-agent w PATH ani w repozytoryjnym .venv." >&2
  exit 1
fi
log_dir="$app_dir/logs"
mkdir -p "$HOME/Library/LaunchAgents" "$log_dir"

escaped_app=${app_dir//&/&amp;}
escaped_app=${escaped_app//</&lt;}
escaped_app=${escaped_app//>/&gt;}
escaped_executable=${executable//&/&amp;}
escaped_executable=${escaped_executable//</&lt;}
escaped_executable=${escaped_executable//>/&gt;}

for component in agent worker; do
  label="pl.marketplace-listing-agent.$component"
  plist_path="$HOME/Library/LaunchAgents/$label.plist"
  template="$script_dir/$label.plist.template"
  sed \
    -e "s|__APP_DIR__|$escaped_app|g" \
    -e "s|__EXECUTABLE__|$escaped_executable|g" \
    "$template" > "$plist_path"
  chmod 600 "$plist_path"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist_path"
  launchctl enable "gui/$(id -u)/$label"
  echo "Zainstalowano $plist_path"
done
