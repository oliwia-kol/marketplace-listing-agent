#!/bin/zsh
set -eu

project_dir="${0:A:h:h}"
label="pl.marketplace-listing-agent.agent"
plist_path="$HOME/Library/LaunchAgents/$label.plist"
log_dir="$project_dir/data/logs"
mkdir -p "$HOME/Library/LaunchAgents" "$log_dir"

escaped_project=${project_dir//&/&amp;}
escaped_project=${escaped_project//</&lt;}
escaped_project=${escaped_project//>/&gt;}

sed \
  -e "s|__PROJECT_DIR__|$escaped_project|g" \
  "$project_dir/scripts/pl.marketplace-listing-agent.agent.plist.template" > "$plist_path"

launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$plist_path"
launchctl enable "gui/$(id -u)/$label"
echo "Zainstalowano $plist_path"
