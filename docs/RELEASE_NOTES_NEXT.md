# Next release — Draft

## Web project hub and Map Reconstruction migration

- Added a lightweight static HappyMeasure project hub for GitHub Pages.
- Added direct launch links for the independently deployed Map Reconstruction and IV Fitter browser applications.
- Retired the legacy desktop Map Reconstruction application from the HappyMeasure repository, including its Qt source, tests, optional dependencies, launcher, packaging path, release screenshots and active owner documentation.
- Future Map Reconstruction development and deployment belongs to `Xiaolong-6/HM-Map-Reconstruction`.
- Simplified HappyMeasure CI/release packaging back to the desktop measurement application plus the static Pages hub.
- Added a Pages workflow that validates local links/assets on pull requests and deploys `web/` from `main`.

Add only changes intended for the next public release. Published 1.2b details belong in `CHANGELOG.md` and the immutable GitHub Release record.
