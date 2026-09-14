# Operations

## Install and diagnose

```bash
uv sync --locked --extra dev --no-editable
.venv/bin/marketplace-listing-agent doctor --scope core
.venv/bin/marketplace-listing-agent doctor --scope models --probe
.venv/bin/marketplace-listing-agent doctor --scope telegram
.venv/bin/marketplace-listing-agent doctor --scope browser
```

The non-editable install is intentional: it tests the built package and avoids a Python
3.14 behavior that skips hidden editable `.pth` files. Runtime data is installed under
`~/Library/Application Support/Marketplace Listing Agent` with private directory/file
permissions. Repository defaults are copied only when a corresponding runtime file does
not exist.

`doctor` exits non-zero if a selected scope fails. The core scope checks Python, writable
directories, YAML, SQLite integrity and schema version. Model probing performs a minimal
real structured inference.

Create a redacted reproducibility manifest when recording a benchmark or release:

```bash
.venv/bin/marketplace-listing-agent manifest --destination environment-manifest.json
```

It contains commit state, platform, model role configuration and hashes of configs and
goldens. It contains no tokens, prompts, private content or absolute application paths.

## Run

```bash
.venv/bin/marketplace-listing-agent configure-token
.venv/bin/marketplace-listing-agent run
```

In a second terminal:

```bash
.venv/bin/marketplace-listing-agent worker
```

The orchestrator and worker share SQLite but are separate processes. Only the worker owns
the sales profile. Run one worker for that profile. `SingletonLock` detection in `doctor`
warns when Chrome already owns it.

After installing the wheel on macOS, `scripts/install-launch-agent.sh` installs two
LaunchAgents: one for the Telegram orchestrator and one for the browser worker. The
matching uninstall script stops and removes both service definitions while preserving
application data.

Useful commands:

```bash
.venv/bin/marketplace-listing-agent worker --once
.venv/bin/marketplace-listing-agent resume-job JOB_ID INTERVENTION_ID
.venv/bin/marketplace-listing-agent cancel-job JOB_ID
.venv/bin/marketplace-listing-agent emergency-stop
.venv/bin/marketplace-listing-agent reconcile-job JOB_ID
```

`resume-job` only returns work to the queue. The worker rechecks CAPTCHA/login/form state.
`reconcile-job` reads an uncertain post-submit outcome and never clicks submit.
An abandoned preparation lease returns to the queue after 15 minutes. An abandoned
submit becomes `unknown` and is never retried automatically.

## Publication gate

Form preparation requires a user-approved snapshot. A ready job still cannot publish.
Telegram `/wystaw JOB_ID` shows the exact content, price, category and snapshot hash and
creates a second one-time approval.

Live submit is disabled by default. It may be enabled only for a controlled run:

```dotenv
MARKETPLACE_AGENT_ALLOW_LIVE_SUBMIT=true
```

Before enabling it, validate the current signed-in Polish form controls, fees and final
button for one portal. Keep the generated preview visible. A real listing requires a
separate, concrete user authorization for that exact snapshot.

## Backup and recovery

```bash
.venv/bin/marketplace-listing-agent backup --destination ~/MarketplaceBackups
.venv/bin/marketplace-listing-agent restore-backup BACKUP_DIR NEW_EMPTY_DATA_DIR
```

Backup uses the SQLite Backup API for a transactionally consistent copy. Restore refuses
to overwrite a non-empty directory. Run core diagnostics against the restored location
before switching the application configuration.

## Evaluation and monitoring

```bash
.venv/bin/marketplace-listing-agent eval --suite price_math
.venv/bin/marketplace-listing-agent eval --suite facts
.venv/bin/marketplace-listing-agent eval --suite copy_quality --split selection --limit 10
.venv/bin/marketplace-listing-agent report --run-id RUN_ID
.venv/bin/marketplace-listing-agent copy-report --run-id RUN_ID
```

Model fallback is disabled during evaluation. Reports include dataset/config hashes,
commit and environment metadata. Use `--repeats`, `--temperature`, `--top-p`, `--top-k`
and `--seed` for reproducible comparisons. The local run report includes only allow-listed
telemetry. Copy diagnostics retain redacted brief/draft/audit stages for 30 days; a manual
`copy-rate` score is bound to the displayed variant hash.

## Docker

```bash
docker compose config --quiet
docker compose build app-check research-proxy
docker compose run --rm app-check
docker compose --profile research up research-worker
```

The research profile has no host data mounts and reaches public networks only through the
CONNECT proxy. On 2026-09-13 Docker Desktop 29.4.0, both image builds and the container
core doctor passed. An integration check reached public HTTPS through the proxy, rejected
localhost and failed direct egress when environment proxies were ignored.

If an anonymous public-image pull hangs in the macOS credential helper, do not delete the
saved Docker configuration. Use a temporary empty config for the pull, then build with
the normal config so Compose plugins remain available:

```bash
mkdir -p /private/tmp/shopper-docker-config
printf '{}\n' > /private/tmp/shopper-docker-config/config.json
DOCKER_CONFIG=/private/tmp/shopper-docker-config docker pull python:3.12-slim
docker compose build app-check research-proxy
```

## MCP

Configure an MCP host to start:

```bash
.venv/bin/marketplace-listing-agent-mcp
```

Transport is local stdio. Logs must remain on stderr because stdout carries protocol
messages. The server does not contain passwords, sessions or listing mutation payloads.
