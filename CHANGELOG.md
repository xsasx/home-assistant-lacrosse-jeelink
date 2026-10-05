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

Community testing of temperature-only models such as the **Technoline TX29D-IT** and **Technoline TX29-IT** is especially welcome before the final `v0.2.0` release.
