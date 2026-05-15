"""Single runtime version source for HappyMeasure.

Keep the Python package import name (`keith_ivt`) until the planned
packaging/namespace cleanup.  Do not duplicate the runtime version in UI code;
validation tests compare this file with pyproject.toml and the handoff docs.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "keith_ivt"  # legacy import namespace; planned cleanup in the next packaging release
APP_CODENAME = "pre-hardware validation alpha"
VERSION = "0.7a1"
__version__ = VERSION
RELEASE_STAGE = "pre-hardware validation alpha"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "0.7a1: centralizes version validation, adds pre-hardware safety and "
    "mock-command tests, adds trace multi-select delete via context menu/Delete key, "
    "and documents the hardware validation protocol. PACKAGE_NAME remains keith_ivt "
    "for compatibility and is explicitly deferred to the next packaging/namespace cleanup."
)
__build_note__ = BUILD_NOTE
