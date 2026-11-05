
# LaCrosse Jeelink for Home Assistant

A modern Home Assistant custom integration for LaCrosse / Technoline wireless temperature and humidity sensors received through a JeeLink USB radio gateway.

The project is intended as a UI-configurable replacement for the legacy YAML-only LaCrosse sensor platform.

Each physical radio sensor is represented as one Home Assistant device with its related entities grouped underneath it.

> **Current beta:** [v0.3.0-beta.5](https://github.com/xsasx/home-assistant-lacrosse-jeelink/releases/tag/0.3.0-beta.5)  
> This beta improves humidity handling, filters invalid readings, and tracks humidity availability independently. TX25TP-IT dual-temperature support is also available for community testing.

## 🗺️ Development roadmap

See the [public development roadmap](ROADMAP.md) for planned features, upcoming versions, and ways to contribute. Follow progress through [GitHub milestones](https://github.com/xsasx/home-assistant-lacrosse-jeelink/milestones).

## ☕ Support the project

If this integration is useful to you and you'd like to support its development, you can buy me a coffee. ☕

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/xsas1337)

Thank you for your support! ❤️

## ✅ Tested devices

The following LaCrosse / Technoline sensors have been successfully tested with this integration:

| Model | Temperature | Humidity | Status |
|---|:---:|:---:|---|
| Technoline TX29DTH-IT | ✅ | ✅ | Tested |
| Technoline TX35DTH-IT | ✅ | ✅ | Tested |
| Technoline TX29D-IT | ✅ | ❌ | Tested |
| Technoline TX29-IT | ✅ | ❌ | Tested |
| Technoline TX25TP-IT | ✅ (internal + external) | ❌ | Tested with 4 devices (community) |

### Temperature-only sensors

The **TX25TP-IT** is a dual-temperature sensor. Enable **Dual-temperature sensor (TX25TP-IT)** in sensor settings to expose separate internal and external temperature entities. Humidity is not supported. Community testing with four devices confirmed separate, plausible readings for both channels.

The **TX29D-IT** and **TX29-IT** are temperature-only sensors and do not provide humidity measurements.

These sensors may report an invalid humidity value of `106 %`. Starting with v0.3.0-beta.5, invalid humidity values are ignored; the humidity entity may show as unavailable while temperature readings continue.

Other compatible LaCrosse / Technoline sensors may also work even if they are not listed here.

If you successfully test another model, please let me know through GitHub Issues.

## Features

- UI setup through **Settings → Devices & services**
- JeeLink serial connection via configurable device path and baud rate
- Multiple LaCrosse sensors per JeeLink
- One Home Assistant device per physical LaCrosse sensor
- Temperature entity
- Humidity entity
- Battery-low binary sensor
- Stable Home Assistant entity/device registry integration
- Area assignment in the Home Assistant UI
- Configurable availability timeout
- Sensor discovery and management through integration options
- Detection of already configured radio IDs
- English and German UI translations
- Optional raw telegram diagnostics for troubleshooting

## Requirements

- Home Assistant 2026.4 or newer
- JeeLink-compatible USB receiver
- `pylacrosse>=0.4` (installed automatically by Home Assistant)
- The JeeLink serial device must be accessible to Home Assistant

## Installation with HACS

Until this repository is included in the default HACS catalog:

1. Open HACS.
2. Add this GitHub repository as a **Custom repository** with category **Integration**.
3. Install **LaCrosse Jeelink**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**.
6. Search for **LaCrosse Jeelink**.
7. Configure the serial device, typically `/dev/ttyUSB0`, and baud rate, typically `57600`.
8. Open **Configure** on the new integration to discover and manage your LaCrosse sensors.

If `/dev/serial/by-id/...` is available, prefer that stable device path over `/dev/ttyUSB0`.

### Installing beta releases

To test a beta release:

1. Open HACS.
2. Navigate to **LaCrosse Jeelink**.
3. Open the three-dot menu.
4. Select **Redownload**.
5. Enable **Show beta versions**, if available.
6. Select the desired beta release.
7. Download and restart Home Assistant.

If the beta is not listed, make sure the GitHub release has been published and HACS has refreshed the repository information.

## Migrating from the legacy LaCrosse integration

Do not run the legacy integration and LaCrosse Jeelink against the same serial port at the same time. Only one process can reliably own the JeeLink connection.

Before configuring this integration, disable or remove the old LaCrosse YAML platform and restart Home Assistant.

Then add the JeeLink and recreate each physical sensor using its current radio ID.

The old legacy entities can be removed after you have verified that the new devices receive valid values.

## Sensor model

A configured physical sensor appears in Home Assistant approximately like this:

```text
Waschküche
├── Temperature
├── Humidity
└── Battery low
```

Assign the device to an Area once and all related entities stay grouped with the physical sensor.

## Sensor discovery and management

LaCrosse Jeelink provides sensor discovery through the Home Assistant integration options.

Open:

**Settings → Devices & services → LaCrosse Jeelink → Configure**

Depending on the available options, you can:

- Discover radio IDs currently received by the JeeLink
- Identify newly detected sensors
- Recognize already configured radio IDs
- Add discovered sensors to Home Assistant
- Remove configured sensors

Discovery depends on actual radio transmissions. A sensor may take some time to appear.

A detected radio ID does not necessarily mean the transmitter has been positively identified as a specific sensor model.

## Radio IDs

LaCrosse radio IDs are received from the JeeLink and may change after a battery replacement or power cycle on some transmitters.

If this happens, remove the affected sensor from the integration options and add it again with the new radio ID.

Radio IDs alone cannot reliably identify a physical sensor or prove that a received telegram is valid.

## 🔬 Raw telegram diagnostics (v0.3.0-beta.3)

Starting with **v0.3.0-beta.3**, LaCrosse Jeelink includes optional raw telegram diagnostics.

This feature is intended for troubleshooting:

- Unexpected or unknown radio IDs
- Possible duplicate or changing radio IDs
- Unsupported or unrecognized telegram formats
- Sensor discovery problems
- Differences between received radio data and Home Assistant sensor values

**Raw telegram diagnostics are disabled by default.**

Normal users do not need to enable this feature.

### Step 1 – Enable raw telegram diagnostics

1. Open **Settings → Devices & services**.
2. Find **LaCrosse Jeelink**.
3. Click **Configure**.
4. Select **Raw telegram diagnostics** (*Rohtelegramm-Diagnose*).
5. Enable the diagnostic checkbox.
6. Confirm with **Submit / OK**.

The integration reloads using the diagnostic receiver.

### Step 2 – Enable DEBUG logging

Open **Developer tools → Actions** in Home Assistant.

Select **YAML mode** and execute:

```yaml
action: logger.set_level
data:
  custom_components.lacrosse_jeelink.diagnostic_receiver: debug
```

This enables DEBUG logging for the diagnostic receiver.

### Step 3 – Collect received telegrams

Wait a few minutes for your sensors to transmit.

You can inspect the logs under:

**Settings → System → Logs**

On Home Assistant OS, you can also use the terminal:

```bash
ha core logs --lines 500 2>&1 | grep -iE "JeeLink raw telegram|JeeLink unrecognized telegram"
```

Example output:

```text
JeeLink raw telegram: 'OK 9 10 1 4 186 53'
JeeLink raw telegram: 'OK 9 60 1 4 202 55'
```

These examples are illustrative and do not represent guaranteed sensor values.

The receiver uses two diagnostic prefixes:

| Log prefix | Meaning |
|---|---|
| `JeeLink raw telegram` | Telegram matches the format recognized by pylacrosse |
| `JeeLink unrecognized telegram` | Non-empty telegram does not match the expected format |

Empty serial reads and whitespace-only lines are not logged.

**Important:** A telegram matching the expected format is not automatically proof that the radio transmission is genuine or error-free.

The diagnostic receiver preserves the normal sensor parsing and callback behavior.

### Step 4 – Report unexpected radio IDs

If you see unexpected sensor IDs, please open a GitHub Issue:

https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues

Include:

- Your sensor model, if known
- Home Assistant version
- LaCrosse Jeelink integration version
- JeeLink receiver model
- Expected radio IDs
- Unexpected radio IDs
- Several consecutive raw telegrams showing the issue
- Whether the issue occurs after replacing batteries or restarting the sensor

Please include actual received telegrams rather than reconstructed examples.

### Step 5 – Disable diagnostics afterwards

Raw telegram logging can generate many DEBUG entries.

Once troubleshooting is complete:

1. Open **LaCrosse Jeelink → Configure → Raw telegram diagnostics**.
2. Disable the diagnostic checkbox.
3. Confirm with **Submit / OK**.

Then restore the normal log level through **Developer tools → Actions**:

```yaml
action: logger.set_level
data:
  custom_components.lacrosse_jeelink.diagnostic_receiver: warning
```

Disabling the diagnostic option restores the normal `pylacrosse` receiver.

## Troubleshooting

For general integration troubleshooting, you can enable DEBUG logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.lacrosse_jeelink: debug
    pylacrosse: debug
```

Restart Home Assistant after modifying this configuration.

Common causes of missing sensor data include:

- Incorrect serial device path
- Serial port already in use by another integration
- Incorrect baud rate
- Changed LaCrosse radio ID
- Weak or missing radio transmissions
- Sensor batteries requiring replacement

For raw serial telegram analysis, use the optional diagnostic feature described above.

## Development status

This project is currently an early release.

Please test beta versions on a Home Assistant installation with a recent backup before relying on them for critical monitoring.

Bug reports, compatibility feedback, and contributions are welcome.

**GitHub repository:**  
https://github.com/xsasx/home-assistant-lacrosse-jeelink

**Issue tracker:**  
https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues

## License

The integration code is licensed under the Apache License 2.0.

`pylacrosse` is a separate runtime dependency and is distributed under its own license (LGPL-2.1-or-later). It is not bundled in this repository.
