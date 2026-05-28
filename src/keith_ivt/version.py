"""Single runtime version source for HappyMeasure.

HappyMeasure is the product and public Python package name.  The historical
``keith_ivt`` namespace remains as a compatibility layer for existing imports,
tests, and local launch scripts used during the alpha migration.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.1 beta 3"
VERSION = "1.1b3"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.1b3: adds Keithley front-panel current range control with SCPI accessors, "
    "deterministic simulator support, sweep-runner range-change settling, and "
    "polished front-panel range popup layout. Also fixes NPLC validation for "
    "constant-time sweeps and CSV import/export metadata round-trip."
)
__build_note__ = BUILD_NOTE
