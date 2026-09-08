from __future__ import annotations

import subprocess

KEYCHAIN_SERVICE = "marketplace-listing-agent.telegram"


def read_keychain_token(account: str = "default") -> str | None:
    """Read a token from macOS Keychain without ever printing it."""
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            account,
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or None if result.returncode == 0 else None


def save_keychain_token(token: str, account: str = "default") -> None:
    """Store/replace the token; called only by the explicit configure command."""
    subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            account,
            "-w",
            token,
        ],
        check=True,
    )
