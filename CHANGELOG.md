# Changelog

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

- Added LaCrosse sensor discovery / radio ID scanner
- All sensors received by the Jeelink can now be displayed directly in the Home Assistant UI
- Displays radio ID, temperature, humidity and battery status
- Already configured radio IDs are recognized automatically
- New/unconfigured sensors are marked as `NEW`
- Discovered sensors can be selected and added directly from the UI
- External `pylacrosse scan` is no longer required to determine a sensor ID

### Fixed

- Fixed sensor name handling when removing configured sensors

### Testing

This is a beta release.

Discovery of already configured sensors has been successfully tested with multiple sensors.

Testing with additional unconfigured LaCrosse / Technoline sensors is especially welcome. In particular, feedback on the complete discovery workflow is appreciated:

`discover → NEW → select → name → add device`

## 0.1.0 - 2026-09-08

- Initial public development release.
- Home Assistant config flow for Jeelink serial device and baud rate.
- Options flow for adding and removing LaCrosse radio sensors.
- Device Registry grouping per physical sensor.
- Temperature, humidity and battery-low entities.
- Availability timeout.
- German and English translations.
- HACS and hassfest validation workflows.
