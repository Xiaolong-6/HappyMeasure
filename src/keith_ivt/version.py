"""Single runtime version source for HappyMeasure.

``VERSION`` is the release-candidate identity. During the active 1.2b release
freeze it remains unchanged across screenshot, documentation, packaging, and
release-only fix commits. The freeze ends after publication; see
``docs/VERSIONING.md`` and ``tools/release/RELEASE_FREEZE_MARKER``.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.2 beta"
VERSION = "1.2b"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "1.2b release candidate: version identity is frozen through screenshot, packaging, "
    "and release finalization."
)
__build_note__ = BUILD_NOTE
