"""Single runtime version source for HappyMeasure.

HappyMeasure is the product and public Python package name.  The historical
``keith_ivt`` namespace remains as a compatibility layer for existing imports,
tests, and local launch scripts used during the alpha migration.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "pre-hardware validation alpha"
VERSION = "0.7a1"
__version__ = VERSION
RELEASE_STAGE = "pre-hardware validation alpha"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "0.7a1: keeps HappyMeasure as the public package/entry namespace, "
    "retains keith_ivt as a legacy compatibility namespace, centralizes "
    "state transitions, adds non-intrusive update reminders, and documents "
    "the pre-hardware validation protocol."
)
__build_note__ = BUILD_NOTE
