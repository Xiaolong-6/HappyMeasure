"""Single runtime version source for HappyMeasure.

HappyMeasure is the product and public Python package name.  The historical
``keith_ivt`` namespace remains as a compatibility layer for existing imports,
tests, and local launch scripts used during the alpha migration.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.1 beta 4"
VERSION = "1.1b4"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.1b4: replaces Adaptive row controls with a multiline segment editor, "
    "makes presets exact Hardware and Sweep snapshots, restores defaults for "
    "empty numeric inputs, preserves requested setpoints across range changes, "
    "and hardens update-check shutdown behavior."
)
__build_note__ = BUILD_NOTE
