# Samsung TV Local (QN90B)

A sibling component to LocalThings for the QN90B TVs, **100% local** — it
talks to the TV directly over the remote-control WebSocket (port 8002, TLS)
plus **Wake-on-LAN** — no SmartThings, no cloud, no fees.

> LocalThings (mbillow) controls Samsung appliances over **CoAP/DTLS**
> (fridges, washers, ...). The **QN90B does not speak CoAP/DTLS** (verified
> against the TV), so this component uses the TV's own WebSocket transport
> (the same protocol family as the stock HA `samsungtv` integration, but as
> part of this fork).

## Features

- **Power**: on via WOL (MAC), off via `KEY_POWER`, on/off state
- **Volume**: up/down/absolute set, mute + volume level state
- **Source/input**: list (`ed.sourcesChanged`) + direct switch
  (`ed.setSource` — best-effort; falls back to cycling `KEY_SOURCE`)
- **Apps**: launch via `media_player.play_media(media_type="app",
  media_id="<id or name>")` + shortcut buttons (Netflix, YouTube, Prime,
  Disney+, Spotify)
- **Media**: play/pause/stop/ff/rew (keys)
- **Remote**: `remote.send_command` with friendly names or raw `KEY_*`
  codes (e.g. `home`, `source`, `ok` — see `const.KEYS`)

## Installation

Copy `custom_components/samsung_tv_local/` into the `custom_components`
directory of your Home Assistant and restart (or install via HACS as a local
repository).

## Configuration

1. **Settings → Devices & Services → Add Integration → "Samsung TV Local
   (QN90B)"**
2. Enter the TV **IP**, the **MAC** (for WOL; Samsung TVs have separate MACs
   for WiFi and Ethernet — use the one for the interface in use) and a name.
3. Authentication (choose one):
   - **Existing token**: paste the token from the stock `samsungtv` config
     entry (in `.storage/core.config_entries`) — the pragmatic path, no
     pairing needed.
   - **Allow popup pairing**: an "Allow" popup appears on the TV; press Allow
     and the token is granted automatically (no PIN — see below).

## How pairing works (validated on the QN90B)

The TV has **two independent pairing mechanisms**, and they behave very
differently:

### 1. Classic WebSocket pairing (the one this component uses — no PIN)

```
1. Client connects to wss://<tv>:8002 ... (TLS) WITHOUT a token
2. The TV replies with the ms.channel.connect event whose data.token is a
   freshly granted auth token
3. The client stores the token and sends it as ?token=<token> on every
   subsequent connection
```

- **No PIN, and usually no popup.** On the QN90B the token grant is
  automatic while the TV is on — the `ms.channel.connect` event
  arrives immediately with the token.
- The TV may show an "Allow" popup **only the first time** a client name is
  seen (or after the paired-client list is cleared). The popup renders the
  client name; a "[Invalid UTF-8]" label is a cosmetic rendering bug of the
  TV, not a real problem. If a popup appears, press Allow and the token
  arrives right after.
- The TV **remembers authorized clients by name**; later connections with an
  already-authorized name rotate the token silently (no popup). A network
  reset does **not** clear the authorized list. To force a fresh popup, use
  a different client name.
- The stored token keeps working across connections (it is only rotated when
  connecting without a token).

### 2. Encrypted SPC pairing (port 8080 — NOT used by this component)

The TV also exposes the newer "encrypted" (SmartThings-style) pairing: an
app opens the **CloudPINPage** (port 8080) and the TV shows an **8-digit
PIN** (e.g. `1234-5678`). That flow performs a Diffie-Hellman/AES handshake
(`/ws/pairing`) and yields a token + session id used by an encrypted
socket.io session.

- This is a **separate mechanism** from the WebSocket remote. On this
  firmware the SPC endpoint (`/ws/pairing`) returns 404, so the encrypted
  path is not available/needed for remote control here.
- If you ever saw an 8-digit PIN on the TV while testing, it came from this
  encrypted page (or from the stock SmartThings app), not from the classic
  pairing.

## Protocol notes (validated live on a QN90B)

- The remote WebSocket is on port **8002 over TLS** (`wss://` with a
  self-signed certificate; plain `ws://` is refused by this firmware).
- The TV only accepts the socket while powered on; when off, WOL only.
- No special TV setting is required — the socket is reachable whenever the
  TV is on. The "**IP Remote**" setting is for remote *configuration* of the
  TV (a different feature), and "**Remote Management**" is for Samsung
  remote support; **neither gates the WebSocket**. The only authorization is
  the one-time Allow popup (validated with both toggles on and off).
- Power-on via WOL and key control (volume up/down, mute, home, power off)
  are validated against real hardware.
- Volume/source **state queries** (`ms.channel.emit` / `ed.volumeChanged`)
  are not answered by every QN90B firmware revision — key-based control
  still works, but state may be unavailable on some units.
- `ed.setSource` (direct input switch) is a flagged guess — some firmware
  ignores it; the component falls back to cycling `KEY_SOURCE`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Socket never answers (TLS handshake fails) | TV is off or unreachable — check the IP / power it on (WOL) |
| `No Authorized` on commands | Token missing/expired — reconnect without a token to get a fresh one |
| No popup appears during pairing | Normal — the token is granted silently; a popup only shows on first-time authorization |
| TV shows "on" while the screen is off / WOL doesn't wake it | The TV's "**Instant On**" is ON (Settings → General & Privacy → Power and Energy Saving) — it keeps the network alive in standby. Turn it off for true deep-off, where WOL works and power state is accurate |
| Volume level shows nothing | Firmware revision doesn't answer state queries — only key control available |
