# ADR 0008: Docker limits research authority; MCP uses local stdio

Status: amended and egress boundary verified locally, 2026-09-16.

The application research browser runs on the Mac and is required to use a loopback-only
Docker CONNECT proxy. The proxy runs as a non-root user with a read-only filesystem,
dropped capabilities and resource limits. It rejects mixed or private DNS answers and
pins the verified IP for the connection. This is an egress boundary, not process or
filesystem isolation of the browser; documentation and CV claims must keep that limit.

MCP uses the official Python SDK v2 over local stdio. Tools accept identifiers and invoke
the same repository rules as Telegram; they do not accept new listing payloads, prices
or credentials. MCP is an interface, not a sandbox.
