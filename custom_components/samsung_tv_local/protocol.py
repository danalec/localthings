"""Local transport for Samsung QN90B TVs.

The QN90B exposes the remote-control WebSocket on port 8002 over TLS
(wss:// with a self-signed certificate). A TV only accepts commands while it
is powered on; power-on is done via a Wake-on-LAN magic packet.

Commands require an auth token. Two ways to obtain one:
  * the classic Pin4 pairing flow over the same WebSocket (works on many
    models, see `pair`), or
  * reuse the token already granted by another client (e.g. the stock HA
    `samsungtv` integration config entry) - the pragmatic path.

No cloud, no SmartThings.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import socket
import ssl
import urllib.parse

import websockets
from websockets.exceptions import ConnectionClosedError

_LOGGER = logging.getLogger(__name__)

REMOTE_CHANNEL = "/api/v2/channels/samsung.remote.control"


def _serialize_name(name: str) -> str:
    """Base64-encode the client name for the URL query.

    Samsung TVs decode this value and render it in the Allow popup; a raw
    (non-Base64) name decodes to garbage and shows as "[Invalid UTF-8]".
    """
    return base64.b64encode(name.encode("utf-8")).decode("ascii")


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class RemoteError(Exception):
    """The TV did not answer as expected."""


class AuthError(RemoteError):
    """The stored token was rejected (expired/revoked)."""


class SamsungRemote:
    """One remote-control WebSocket session to a TV."""

    def __init__(self, host, name="LocalThings", token=None, port=8002):
        self.host = host
        self.name = name
        self.token = token
        self.port = port
        self._ws = None

    def _uri(self, include_token):
        query = {"name": _serialize_name(self.name)}
        if include_token and self.token:
            query["token"] = self.token
        return f"wss://{self.host}:{self.port}{REMOTE_CHANNEL}?" + urllib.parse.urlencode(query)

    async def connect(self):
        self._ws = await websockets.connect(
            self._uri(include_token=True), ssl=_ssl_context(), open_timeout=8
        )
        # Drain startup events until the channel-connect confirmation.
        for _ in range(5):
            try:
                msg = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=4))
            except TimeoutError:
                break
            except ConnectionClosedError as exc:
                raise RemoteError(f"connection closed during handshake ({exc.code})") from exc
            event = msg.get("event")
            if event == "ms.channel.connect":
                break
            if event in ("ms.channel.unauthorized", "ms.channel.timeOut"):
                raise AuthError(f"token rejected ({event})")

    async def close(self):
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self):
        if self._ws is None:
            await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _send(self, payload):
        if self._ws is None:
            raise RemoteError("not connected")
        await self._ws.send(json.dumps(payload))

    async def _recv(self, recv_timeout: float = 4.0):
        if self._ws is None:
            raise RemoteError("not connected")
        return json.loads(await asyncio.wait_for(self._ws.recv(), timeout=recv_timeout))

    async def send_key(self, key):
        await self._send(
            {
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Click",
                    "DataOfCmd": key,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey",
                },
            }
        )

    async def send_key_checked(self, key):
        """Send a key and detect an auth rejection.

        The QN90B replies `ms.error {message: "No Authorized"}` to rejected
        commands (and stays silent on accepted ones), so a short read is
        enough to tell an expired token apart.
        """
        await self.send_key(key)
        try:
            msg = await self._recv(recv_timeout=1.0)
        except TimeoutError:
            return  # accepted: no reply on success
        data = msg.get("data") or {}
        if msg.get("event") == "ms.error" and data.get("message") == "No Authorized":
            raise AuthError("No Authorized")

    async def _emit(self, event):
        """Query state and wait for the matching reply (bounded by timeout)."""
        await self._send({"method": "ms.channel.emit", "params": {"event": event, "to": "host"}})
        for _ in range(20):
            try:
                msg = await self._recv(recv_timeout=4)
            except TimeoutError:
                raise RemoteError(f"no reply for {event}") from None
            data = msg.get("data")
            if (
                msg.get("event") == "ms.error"
                and isinstance(data, dict)
                and data.get("message") == "No Authorized"
            ):
                raise AuthError("No Authorized")
            if isinstance(data, dict) and data.get("event") == event:
                return data.get("data", {})
            if msg.get("event") == event:
                return msg.get("data", {})
        raise RemoteError(f"no reply for {event}")

    async def get_volume(self):
        data = await self._emit("ed.volumeChanged")
        return {
            "volume": data.get("volume"),
            "mute": bool(data.get("mute", False)),
            "max": data.get("maxVolume"),
        }

    async def get_sources(self):
        data = await self._emit("ed.sourcesChanged")
        return data.get("sources", [])

    async def launch_app(self, app_id):
        await self._send(
            {
                "method": "ms.channel.emit",
                "params": {
                    "event": "ed.apps.launch",
                    "to": "host",
                    "data": {
                        "action_type": "DEEP_LINK",
                        "appId": app_id,
                        "metaTag": "",
                    },
                },
            }
        )

    async def set_source(self, source_id):
        """Best-effort direct source switch (see README)."""
        await self._send(
            {
                "method": "ms.channel.emit",
                "params": {
                    "event": "ed.setSource",
                    "to": "host",
                    "data": {"id": source_id},
                },
            }
        )


async def pair(host, name="LocalThings", port=8002):
    """Pair by triggering the TV's allow popup and reading the granted token.

    On QN90B firmware the TV shows an "Allow" popup (no PIN). After the user
    allows it, the channel-connect event carries the auth token.
    """
    uri = f"wss://{host}:{port}{REMOTE_CHANNEL}?" + urllib.parse.urlencode(
        {"name": _serialize_name(name)}
    )
    last_exc: Exception | None = None
    # Retry the connection: the TV occasionally closes a fresh socket with a
    # protocol error while its remote service is settling.
    for _attempt in range(3):
        try:
            async with websockets.connect(uri, ssl=_ssl_context(), open_timeout=8) as ws:
                # Up to ~2 minutes for the user to press Allow on the TV.
                for _ in range(15):
                    try:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
                    except TimeoutError:
                        continue
                    if msg.get("event") == "ms.channel.connect":
                        token = (msg.get("data") or {}).get("token")
                        if token:
                            return token
        except (ConnectionClosedError, OSError, TimeoutError) as exc:
            last_exc = exc
            await asyncio.sleep(1)
    raise RemoteError(f"no token granted (was the popup allowed?): {last_exc}")


async def is_on(host, token=None, port=8002):
    """A TV only accepts the remote WebSocket while powered on.

    Pass the auth token when available so the probe does not re-trigger the
    TV's Allow popup.
    """
    try:
        tv = SamsungRemote(host, token=token, port=port)
        await tv.connect()
        await tv.close()
        return True
    except Exception:
        return False


async def wake_on_lan(mac, host=None):
    """Send a WOL magic packet for `mac` (00:11:22:33:44:55)."""
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError(f"bad MAC: {mac}")
    packet = b"\xff" * 6 + mac_bytes * 16
    loop = asyncio.get_running_loop()

    def _send():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, ("255.255.255.255", 9))
            if host:
                sock.sendto(packet, (host, 9))

    await loop.run_in_executor(None, _send)
