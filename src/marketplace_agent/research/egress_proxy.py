from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable


async def resolve_public_target(
    host: str,
    port: int,
    resolver: Callable[[str], Awaitable[list[str]]] | None = None,
) -> str:
    """Resolve once and return a public address used for the actual connection."""
    if port not in {80, 443}:
        raise PermissionError("egress proxy permits only ports 80 and 443")

    async def system_resolver(value: str) -> list[str]:
        rows = await asyncio.get_running_loop().getaddrinfo(value, None, type=socket.SOCK_STREAM)
        return list(dict.fromkeys(row[4][0] for row in rows))

    addresses = await (resolver or system_resolver)(host)
    public = []
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if address.is_global:
            public.append(raw)
    if not public or len(public) != len(addresses):
        raise PermissionError("destination resolves to a private or special address")
    return public[0]


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(64 * 1024):
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Minimal CONNECT proxy that constrains research-browser network egress."""
    try:
        request_line = (await reader.readline()).decode("ascii", "strict").strip()
        parts = request_line.split()
        if len(parts) != 3 or parts[0] != "CONNECT":
            raise PermissionError("only HTTPS CONNECT is supported")
        host, separator, raw_port = parts[1].rpartition(":")
        if not separator or not host:
            raise ValueError("invalid CONNECT target")
        port = int(raw_port)
        while await reader.readline() not in {b"\r\n", b"\n", b""}:
            pass
        address = await resolve_public_target(host, port)
        upstream_reader, upstream_writer = await asyncio.open_connection(address, port)
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(
            _pipe(reader, upstream_writer),
            _pipe(upstream_reader, writer),
            return_exceptions=True,
        )
    except Exception:
        writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle_client, "0.0.0.0", 8080)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
