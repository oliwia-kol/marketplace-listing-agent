# Marketplace Listing Agent

A local Python application that turns product photos and notes into reviewed resale
listing drafts. A private Telegram bot guides the user through facts, price research,
listing copy and form preparation for OLX and Allegro Lokalnie.

## Architecture

- **Telegram + LangGraph:** collect input and pause at user decisions.
- **Ollama:** local models propose facts and copy; code checks claims against approved
  facts and product evidence.
- **Playwright research:** collect public offers through a restricted egress proxy.
  Deterministic rules separate item prices from shipping, installments and old prices,
  then calculate statistics from eligible comparables.
- **SQLite:** persist items, checkpoints, immutable listing snapshots, one-time
  approvals and execution jobs.
- **Browser worker:** prepare a form from an approved snapshot in a separate Chrome
  profile. Submission requires a second approval after form readback and is disabled
  by default. A local MCP server exposes narrow operations by ID over `stdio`.

## Run locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), Google Chrome, Docker,
[Ollama](https://ollama.com/) and a private Telegram bot. On macOS the bot token is
stored in Keychain.

```bash
uv sync --locked
cp .env.example .env
# Set MARKETPLACE_AGENT_TELEGRAM_ALLOWED_CHAT_ID in .env.
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull hf.co/speakleash/Bielik-11B-v3.0-Instruct-GGUF:Q4_K_M
docker compose up -d research-proxy
uv run marketplace-listing-agent configure-token
uv run marketplace-listing-agent doctor --scope all
uv run marketplace-listing-agent run
```

Run `uv run marketplace-listing-agent worker` in a separate terminal for browser
jobs. `uv run marketplace-listing-agent --help` lists the other commands.

## For the curious

Two LoRA experiments adapted Qwen3-0.6B for Polish listing prose. The adapters
improved prose format but lost exact facts on held-out product families, so the
application uses the checked copy pipeline instead of either adapter.
