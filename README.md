# Petcube for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration for **Petcube Bites** treat dispensers, reverse-engineered from the official Android app (v8.3.0).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lyntoo&repository=petcube-ha&category=integration)

---

## Supported Devices

| Device | Treats | Strength | Camera |
|--------|--------|----------|--------|
| Petcube Bites | ✅ | ✅ | ⚠️ |
| Petcube Bites 2 | ✅ | ✅ | ⚠️ |
| Petcube Play / Play 2 | ❌ | — | ❌ |

> **Camera note:** Snapshot support requires an active **Petcube Care** subscription (cloud recording). Without Care, the camera entity will appear as unavailable. Live video streaming is not supported (requires WebRTC).

---

## Features

- **Treat button** — Dispense a treat with one tap or via automation
- **Strength selector** — Choose launch strength: Faible / Moyen / Fort (1–3)
- **Camera entity** — Shows the latest recorded snapshot *(Petcube Care subscription required)*
- **Connectivity sensor** — Binary sensor reporting whether the device is online
- **Firmware sensor** — Current firmware version with device metadata as attributes
- **Device grouping** — All entities appear under a single device card in HA
- **Auto-polling** — Device status refreshed every 60 seconds via `DataUpdateCoordinator`

---

## Requirements

- Home Assistant 2023.1 or newer
- A [Petcube](https://petcube.com) account with a Bites device registered
- No extra Python dependencies (uses only stdlib)

---

## Installation

### Via HACS (recommended)

1. Click the badge above, or go to **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/lyntoo/petcube-ha` as an **Integration**
3. Search for **Petcube** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/petcube` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Petcube**
3. Enter your Petcube account email and password
4. Select your device from the list
5. Done — entities will appear automatically under a single device card

---

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.petcube_xxx_online` | Binary sensor | Device connectivity (online / offline) |
| `button.petcube_xxx_treat` | Button | Dispense a treat |
| `select.petcube_xxx_strength` | Select | Launch strength (Faible / Moyen / Fort) |
| `camera.petcube_xxx_camera` | Camera | Latest snapshot (Care required) |
| `sensor.petcube_xxx_firmware` | Sensor | Firmware version + device metadata |

---

## Automation Example

```yaml
alias: Treat at 5pm
trigger:
  - platform: time
    at: "17:00:00"
action:
  - service: select.select_option
    target:
      entity_id: select.petcube_bites_strength
    data:
      option: Fort
  - service: button.press
    target:
      entity_id: button.petcube_bites_treat
```

---

## How It Works

This integration uses the **Petcube REST API** (`api.petcube.com`) with legacy token authentication, discovered by decompiling the official Android APK with [jadx](https://github.com/skylot/jadx).

Key endpoints:
- `POST api/v1/login` → authentication
- `GET api/v1/users/{id}/petcubes` → device listing
- `POST api/v1/deviceActivity/treats/launch/{id}` → treat dispense
- `GET api/v1/petcubes/{id}` → device status (polled every 60s)

---

## Disclaimer

This project is not affiliated with or endorsed by Petcube Inc. Use at your own risk. The API is unofficial and may change without notice.
