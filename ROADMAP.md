# Development Roadmap

This is the planned roadmap for LaCrosse Jeelink. Priorities and release targets may change based on community feedback and testing. No release dates are promised.

## v0.3.0 — Stability & Sensor Compatibility
- TX25TP-IT dual-temperature support ([#9](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues/9)): beta implementation, hardware confirmation pending
- Invalid humidity handling ([#11](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues/11)): beta implementation, community testing pending
- Regression tests and stable release validation

## 0.4.0 — Connection Reliability
- Audit pylacrosse connection handling
- Automatic USB/serial reconnection and receiver health monitoring
- Configurable recovery behavior and diagnostics
- Automated recovery tests

## 0.5.0 — Advanced Sensor Data
- Configurable outlier filtering
- Dew point and absolute humidity entities
- Packet reception diagnostics and data quality monitoring
- UI-based advanced settings

## 0.6.0 — Automation & User Experience
- Optional low-battery and unavailable-sensor alerts
- Ignore unwanted discovered radio IDs
- Safe, assisted radio ID reassignment after battery changes
- Improved sensor management and configuration

## 1.0.0 — Stable & Feature-Rich Release
- Demonstrated long-term reliability
- Broader documented sensor compatibility
- Comprehensive automated tests
- Robust lifecycle management and complete documentation

## Get involved

Community testing and suggestions are welcome. See [issues](https://github.com/xsasx/home-assistant-lacrosse-jeelink/issues), [milestones](https://github.com/xsasx/home-assistant-lacrosse-jeelink/milestones), and [releases](https://github.com/xsasx/home-assistant-lacrosse-jeelink/releases).
