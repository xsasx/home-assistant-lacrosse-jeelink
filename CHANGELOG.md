# Changelog

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
