"""Single runtime version source for HappyMeasure.

``VERSION`` is the internal source-build identity. During active development the
beta serial is incremented by exactly one on every commit. Public release names
and tags are chosen deliberately by a human during release finalization; see
``docs/VERSIONING.md``.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.1 beta 7"
VERSION = "1.1b7"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.1b7 internal build: release-prep documentation/privacy cleanup, live Time-history "
    "controls, developer diagnostics cleanup, safer serial detection, and persistent "
    "backup/log preferences."
)
__build_note__ = BUILD_NOTE
