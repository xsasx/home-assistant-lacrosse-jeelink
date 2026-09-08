# LaCrosse Jeelink for Home Assistant

A modern Home Assistant custom integration for LaCrosse / Technoline wireless temperature and humidity sensors received through a Jeelink USB radio gateway.

The project is intended as a UI-configurable replacement for the legacy YAML-only LaCrosse sensor platform. Each physical radio sensor is represented as one Home Assistant device with its related entities grouped underneath it.

## Features

- UI setup through **Settings → Devices & services**
- Jeelink serial connection via configurable device path and baud rate
- Multiple LaCrosse sensors per Jeelink
- One Home Assistant device per physical LaCrosse sensor
- Temperature entity
- Humidity entity
- Battery-low binary sensor
- Stable Home Assistant entity/device registry integration
- Area assignment in the Home Assistant UI
- Configurable availability timeout
- English and German UI translations

## Requirements

- Home Assistant 2026.4 or newer
- Jeelink-compatible USB receiver
- `pylacrosse==0.4` (installed automatically by Home Assistant)
- The Jeelink serial device must be accessible to Home Assistant

## Installation with HACS

Until this repository is included in the default HACS catalog:

1. Open HACS.
2. Add this GitHub repository as a **Custom repository** with category **Integration**.
3. Install **LaCrosse Jeelink**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**.
6. Search for **LaCrosse Jeelink**.
7. Configure the serial device, typically `/dev/ttyUSB0`, and baud rate, typically `57600`.
8. Open **Configure** on the new integration and add your LaCrosse sensors by name and radio ID.

If `/dev/serial/by-id/...` is available, prefer that stable device path over `/dev/ttyUSB0`.

## Migrating from the legacy LaCrosse integration

Do not run the legacy integration and LaCrosse Jeelink against the same serial port at the same time. Only one process can reliably own the Jeelink connection.

Before configuring this integration, disable or remove the old LaCrosse YAML platform and restart Home Assistant. Then add the Jeelink and recreate each physical sensor using its current radio ID.

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

## Radio IDs

LaCrosse radio IDs are received from the Jeelink and may change after a battery replacement or power cycle on some transmitters. If this happens, remove the affected sensor from the integration options and add it again with the new radio ID.

A future release is planned to make radio-ID changes easier and to discover unknown transmitters automatically.

## Troubleshooting

Enable debug logging for the integration if setup fails or no packets arrive:

```yaml
logger:
  logs:
    custom_components.lacrosse_jeelink: debug
    pylacrosse: debug
```

Common causes are an incorrect serial device path, the serial port already being used by another integration, an incorrect baud rate, or a changed LaCrosse radio ID.

## Development status

This project is currently an early release. Please test it on a Home Assistant backup before relying on it for critical monitoring.

## License

The integration code is licensed under the Apache License 2.0.

`pylacrosse` is a separate runtime dependency and is distributed under its own license (LGPL-2.1-or-later). It is not bundled in this repository.
