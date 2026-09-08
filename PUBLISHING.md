# Publishing checklist

Before the first public HACS release:

1. Replace every occurrence of `xsasx` in the repository.
2. Set the GitHub repository description, for example: `Home Assistant integration for LaCrosse sensors via Jeelink USB`.
3. Add GitHub topics such as `home-assistant`, `hacs`, `lacrosse`, `jeelink`, `technoline`, `custom-component`.
4. Push the repository and verify both GitHub Actions jobs pass.
5. Add the repository to HACS as a custom repository and test installation on Home Assistant.
6. Create a `v0.1.0` GitHub release after successful testing.
7. Add branding to the `home-assistant/brands` repository before applying for inclusion in the default HACS catalog.
8. Once validation and branding are complete, submit the repository to `hacs/default`.
