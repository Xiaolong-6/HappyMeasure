"""Single runtime version source for HappyMeasure.

HappyMeasure is the product and public Python package name.  The historical
``keith_ivt`` namespace remains as a compatibility layer for existing imports,
tests, and local launch scripts.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.1 beta 6"
VERSION = "1.1b6"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.1b6: hardens long-running Time plotting, Fast acquisition and diagnostics; "
    "adds the staged Map Reconstruction workflow; and closes settings, export, "
    "workspace-lifecycle, and release-validation regressions."
)
__build_note__ = BUILD_NOTE
