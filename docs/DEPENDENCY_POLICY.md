# Dependency update policy

The project uses a locked dependency graph. Runtime and development updates are proposed
monthly by Dependabot and reviewed as ordinary code changes.

Patch and minor updates may be merged after CI, package installation, and relevant local
tests pass. Major updates require a short compatibility note and a targeted regression
test when they affect LangGraph replay, Pydantic schemas, Playwright, SQLite, Telegram,
MCP, or model inference. Security updates take priority, but a green vulnerability scan
does not replace functional testing.

CI receives no marketplace credentials, Telegram token, browser profile, private data,
or model server. Pull requests never run publication, logged-in browser automation, or
local model evaluation.
