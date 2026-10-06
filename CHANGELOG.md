# Changelog

All notable changes to LaCrosse Jeelink are documented in this file.

## v0.2.0

### Added

- Added automatic discovery of LaCrosse / Technoline sensors received by the Jeelink
- Added a discovery workflow for adding previously unconfigured sensors directly from the Home Assistant UI
- Added automatic detection of temperature-only sensors
- Added persistent `has_humidity` capability information for configured sensors
- Added support for radio ID `0`

### Changed

- Replaced the radio ID slider with a numeric input field for easier manual sensor configuration
- Sensor discovery distinguishes between already configured and new sensors
- Sensor discovery only displays humidity when the received humidity value is valid
- Temperature-only sensors no longer create a humidity entity
- Existing sensors configured with earlier versions are automatically migrated when detected as temperature-only
- Changed the `pylacrosse` requirement from an exact version pin to a minimum version requirement to comply with Home Assistant validation

### Fixed

- Fixed temperature-only sensors such as the Technoline TX29D-IT and TX29-IT incorrectly exposing a humidity value of `106 %`
- Existing invalid humidity entities are automatically removed during migration
- Temperature and battery entities remain unchanged when a sensor is migrated to temperature-only
- Removing a configured sensor now also removes its Home Assistant device and associated entities
- Prevents orphaned device and entity registry entries after deleting a sensor

### Tested devices

- Technoline TX29DTH-IT
- Technoline TX35DTH-IT
- Technoline TX29D-IT
- Technoline TX29-IT

### Thanks

Thanks to everyone who tested the beta releases and provided feedback! ❤️


## v0.2.0-beta.3

### Added

- Added automatic detection of temperature-only LaCrosse / Technoline sensors
- Added persistent `has_humidity` capability information for configured sensors

### Changed

- Sensor discovery now only displays humidity when the received humidity value is valid
- Temperature-only sensors no longer create a humidity entity
- Existing sensors configured with earlier versions are automatically migrated when detected as temperature-only

### Fixed

- Fixed temperature-only sensors such as the Technoline TX29D-IT and TX29-IT incorrectly exposing a humidity value of `106 %`
- Existing invalid humidity entities are automatically removed during migration
- Temperature and battery entities remain unchanged when a sensor is migrated to temperature-only

### Testing

The temperature-only sensor migration was tested with an existing configured sensor which previously exposed `106 %` humidity.

The migration was confirmed to:

- automatically detect the temperature-only sensor
- remove the invalid humidity entity
- preserve the temperature entity
- preserve the battery entity
- persist the detected capability across Home Assistant restarts

Humidity-capable sensors were also verified to continue exposing their humidity entities normally.

Community testing of temperature-only models such as the **Technoline TX29D-IT** and **Technoline TX29-IT** was especially requested before the final `v0.2.0` release.


## v0.2.0-beta.2

### Changed

- Replaced the radio ID slider with a numeric input field for easier manual sensor configuration
- Added support for radio ID `0`
- Changed the `pylacrosse` requirement from an exact version pin to a minimum version requirement to comply with Home Assistant validation

### Fixed

- Removing a configured sensor now also removes its Home Assistant device and associated entities
- Prevents orphaned device and entity registry entries after deleting a sensor

### Testing

Sensor discovery was successfully tested by a community user with a previously unconfigured **Technoline TX29DTH-IT**.

The complete discovery workflow was confirmed to work:

`discover → NEW → select → name → add device`

Additional testing of sensor discovery, manual sensor configuration and sensor removal was requested.


## v0.2.0-beta.1

### Added

- Added LaCrosse sensor discovery / radio ID scanning directly in Home Assistant
- Added detection of all LaCrosse sensors received by the Jeelink
- Added display of radio ID, temperature, humidity and battery status during discovery
- Added automatic recognition of already configured radio IDs
- Added `NEW` marking for previously unconfigured sensors
- Added the ability to select, name and add discovered sensors directly from the Home Assistant UI

### Testing

Discovery was successfully tested with multiple already configured sensors.

This beta release introduced the complete discovery workflow:

`discover → NEW → select → name → add device`


## v0.1.0

### Added

- Initial release of LaCrosse Jeelink for Home Assistant
- UI-based configuration
- Jeelink USB radio gateway support
- Support for multiple LaCrosse / Technoline sensors
- Native Home Assistant device grouping
- Temperature sensor entities
- Humidity sensor entities
- Low battery binary sensor entities
- Stable unique IDs
- Device availability timeout
- German and English translations
