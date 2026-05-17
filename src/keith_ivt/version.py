"""Single runtime version source for HappyMeasure.

HappyMeasure is the product and public Python package name.  The historical
``keith_ivt`` namespace remains as a compatibility layer for existing imports,
tests, and local launch scripts used during the alpha migration.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.0 beta"
VERSION = "1.0b1"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.0b1: first beta candidate after alpha hardware smoke testing; "
    "keeps HappyMeasure as the public package/entry namespace, retains "
    "keith_ivt compatibility, hardens sweep safety/state handling, improves "
    "trace export and UI smoke behavior, and keeps full bench validation as "
    "post-release follow-up."
)
__build_note__ = BUILD_NOTE
