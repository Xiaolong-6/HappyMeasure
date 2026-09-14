"""Single runtime version source for HappyMeasure.

``VERSION`` is the internal source-build identity. During active development the
beta serial is incremented by exactly one on every commit. Public release names
and tags are chosen deliberately by a human during release finalization; see
``docs/VERSIONING.md``.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.1 beta 12"
VERSION = "1.1b12"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.1b12 internal build: removes an unreachable current-range formatter "
    "fallback identified by the final coverage audit."
)
__build_note__ = BUILD_NOTE
