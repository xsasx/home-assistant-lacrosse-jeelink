# Changelog

## v0.2.0-beta.3

### Added

- Added automatic detection of temperature-only LaCrosse / Technoline sensors
- Added persistent `has_humidity` capability information for configured sensors

### Changed

- Sensor discovery now only displays humidity when the received humidity value is valid
- Temperature-only sensors no longer create a humidity entity
- Existing sensors configured with earlier versions are automatically migrated when they are detected as temperature-only

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
- persist the detected capability across integration reloads and Home Assistant restarts

Humidity-capable sensors were also verified to continue exposing their humidity entities normally.

Community testing of temperature-only models such as the **Technoline TX29D-IT** and **Technoline TX29-IT** is especially welcome before the final `v0.2.0` release.

## v0.2.0-beta.2

### Changed

- Replaced the radio ID slider with a numeric input field for easier manual sensor configuration
- Radio ID `0` is now supported
- Changed the `pylacrosse` requirement from an exact version pin to a minimum version requirement to comply with Home Assistant validation

### Fixed

- Removing a configured sensor now also removes its Home Assistant device and associated entities
- Prevents orphaned device and entity registry entries after deleting a sensor

### Testing

Sensor discovery has now been successfully tested by a community user with a previously unconfigured **Technoline TX29DTH-IT**.

The complete discovery workflow was confirmed to work:

`discover → NEW → select → name → add device`

This remains a beta release. Additional testing of sensor discovery, manual sensor configuration and sensor removal is welcome.

## v0.2.0-beta.1

### Added

- Added sensor discovery through the existing Jeelink connection
- Added a discovery scanner to the integration options
- Discovered sensors show radio ID, temperature, humidity and battery status
- Unknown discovered sensors are marked as `NEW`
- Already configured sensors are identified by their configured name
- Discovered sensors can be selected and added directly from the UI
- Added runtime discovery cache for received LaCrosse sensor packets

### Changed

- Sensor configuration can now be managed through the Home Assistant UI
- Existing configured radio IDs are detected during discovery

### Notes

The discovery cache is runtime-only and is cleared when the integration or Home Assistant is restarted.

This is a beta release intended for testing the new discovery workflow.
