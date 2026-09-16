# Security model

Protected assets are marketplace sessions, Telegram credentials, user photos, approved
facts, listing authority and pricing integrity. Trust boundaries are Telegram transport,
public web content, local model output, SQLite state, the MCP client and the persistent
sales browser.

| Threat | Enforced control | Failure behavior |
|---|---|---|
| Unsupported model claim | source-tagged facts, user approval, copy audit and deterministic guard | replace or pause |
| Prompt injection in a listing | untrusted data contract; research role has no execution tool | ignore as authority |
| SSRF / DNS rebinding | scheme/port/credential checks, DNS classification, proxy IP pinning | reject destination |
| Wrong price semantics | DOM/JSON-LD/meta observations, currency and price-kind gate | quarantine record |
| Stale approval | immutable photo/content snapshot and version-bound token | reject callback |
| Duplicate local job | deterministic idempotency key and unique constraint | return existing job |
| Two workers claim one job | `BEGIN IMMEDIATE` and conditional update | one owner wins |
| Worker dies while preparing | stale lease watchdog | return reversible work to queue |
| Worker dies while submitting | asymmetric stale lease watchdog | mark `unknown`, never retry |
| CAPTCHA or expired login | durable intervention; no bypass | pause one job |
| Changed form value | readback before ready and again before submit | require new preview |
| Unexpected fee or promotion | blocker detection before submit | pause |
| Lost response after submit | `unknown`; no automatic retry | reconcile by reading state |
| Token or private content in telemetry | fixed event allow-list and error types | data is not collected |
| MCP overreach | local stdio, identifier-only tools, repository-side authorization | reject call |

Copy diagnostics are stored only in local SQLite, with a 30-day expiry. Email addresses
and common token/password patterns are redacted before storage. Redaction is a reducing
control, not a proof that arbitrary personal text is anonymous, so prompts and images are
still excluded from general run telemetry. Product specifications are source-tagged and
kept separate from observations about the sold item.

The persistent sales profile is separate from personal Chrome and is not used by the
research browser. Passwords and OTPs are entered directly into the portal. A local
profile still contains valuable session cookies; 2FA does not protect a stolen valid
cookie, so filesystem and host security remain necessary.

The Docker egress proxy permits HTTPS CONNECT only to ports 80/443, rejects any DNS set
containing private or special addresses, and connects to the checked IP. The application
refuses to create its research browser without a configured proxy. The browser itself
runs on the Mac, so this constrains network destinations but is not a filesystem sandbox.

No control here guarantees protection after full host compromise or detects perfectly
consistent cloaking. Portal UI and terms can change. Real-account use requires a dated
controlled-browser inventory and one explicitly approved end-to-end test.
