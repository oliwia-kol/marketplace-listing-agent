# ADR 0008: Docker limits research authority; MCP uses local stdio

Status: accepted and infrastructure boundary verified locally, 2026-09-13.

The container runs as a non-root user with a read-only filesystem, dropped capabilities,
resource limits and no host secrets. The research network is internal and reaches the
public internet only through a proxy that rejects mixed or private DNS answers and pins
the verified IP for the connection.

MCP uses the official Python SDK v2 over local stdio. Tools accept identifiers and invoke
the same repository rules as Telegram; they do not accept new listing payloads, prices
or credentials. MCP is an interface, not a sandbox.
