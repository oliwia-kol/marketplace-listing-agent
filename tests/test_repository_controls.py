import json

from typer.testing import CliRunner

from marketplace_agent.cli import app
from scripts.scan_secrets import scan_paths
from scripts.validate_jsonl import validate_jsonl


def test_jsonl_validator_rejects_duplicate_ids(tmp_path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text(json.dumps({"id": "same", "input": {}}) + "\n", encoding="utf-8")
    second.write_text(json.dumps({"id": "same", "input": {}}) + "\n", encoding="utf-8")
    errors = validate_jsonl([first, second])
    assert any("duplicate id" in error for error in errors)


def test_secret_scanner_detects_token_without_echoing_it(tmp_path) -> None:
    secret = tmp_path / "secret.txt"
    token = "ghp_" + "a" * 30
    secret.write_text(token, encoding="utf-8")
    findings = scan_paths([secret])
    assert findings == [f"{secret}: possible GitHub token"]
    assert token not in findings[0]


def test_doctor_returns_nonzero_for_missing_telegram(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MARKETPLACE_AGENT_APP_DIR", str(tmp_path))
    monkeypatch.delenv("MARKETPLACE_AGENT_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("MARKETPLACE_AGENT_TELEGRAM_ALLOWED_CHAT_ID", raising=False)
    monkeypatch.setattr("marketplace_agent.diagnostics.read_keychain_token", lambda: None)
    result = CliRunner().invoke(app, ["doctor", "--scope", "telegram"])
    assert result.exit_code == 1
    assert "[FAIL] Telegram token" in result.output
