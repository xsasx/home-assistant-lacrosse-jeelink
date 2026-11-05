# Development Roadmap

This is the planned roadmap for LaCrosse Jeelink. Priorities and release targets may change based on community feedback and testing. No release dates are promised.

## ✅ v0.3.0 — Stability & Sensor Compatibility (Released)

**Stable release:** [v0.3.0](https://github.com/xsasx/home-assistant-lacrosse-jeelink/releases/tag/v0.3.0)

- ✅ TX25TP-IT dual-temperature support ([#9](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues/9)), tested with four physical sensors by the community
- ✅ Invalid humidity handling ([#11](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues/11)): invalid readings do not permanently remove working humidity entities
- ✅ Per-device humidity configuration and entity registry cleanup
- ✅ Ignore and restore unwanted radio IDs ([#7](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues/7))
- ✅ Safer battery-change radio ID reassignment, including protection against ignored IDs
- ✅ Discovery freshness, manual refresh, and optional stale-sensor filter ([#8](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues/8))
- ✅ Automated regression tests and stable release validation

## 🚧 v0.4.0 — Connection Reliability (Next)

- [ ] Audit `pylacrosse` connection handling, error propagation, and clean shutdown
- [ ] Automatic USB/serial reconnection after receiver disconnects or errors
- [ ] Receiver health monitoring (connection status, last packet received, reconnect attempts)
- [ ] Configurable recovery behavior and useful diagnostics
- [ ] Automated tests for connection loss, recovery, and lifecycle behavior

## v0.5.0 — Advanced Sensor Data

- [ ] Configurable outlier filtering
- [ ] Dew point and absolute humidity entities
- [ ] Packet reception diagnostics and data quality monitoring
- [ ] UI-based advanced settings

## v0.6.0 — Automation & User Experience

- [ ] Optional low-battery and unavailable-sensor alerts
- [ ] Further sensor management and configuration improvements

*Note: Ignoring discovered sensors and assisted radio ID reassignment were delivered early in v0.3.0.*

## v1.0.0 — Mature & Feature-Rich Release

- [ ] Demonstrated long-term reliability
- [ ] Broader documented sensor compatibility
- [ ] Comprehensive automated tests
- [ ] Robust lifecycle management and complete documentation

## Get involved

Community testing and suggestions are welcome. See [issues](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues), [milestones](https://github.com/xsasx/home-assistant-lacrosse-jeelink/milestones), and [releases](https://github.com/xsasx/home-assistant-lacrosse-jeelink/releases).
