"""Single runtime version source for HappyMeasure.

HappyMeasure is the product and public Python package name.  The historical
``keith_ivt`` namespace remains as a compatibility layer for existing imports,
tests, and local launch scripts used during the alpha migration.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.1 beta 5"
VERSION = "1.1b5"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.1b5: treats Step as a magnitude, validates sweep configurations before "
    "starting workers, rejects non-finite active values, and recovers the UI "
    "to a reusable idle state after runtime sweep errors."
)
__build_note__ = BUILD_NOTE
