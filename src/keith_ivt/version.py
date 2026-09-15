"""Single runtime version source for HappyMeasure.

``VERSION`` is the internal development identity. Public release ``v1.2b`` remains
fixed at its published tag; post-release development resumes with numbered beta
serials. See ``docs/VERSIONING.md``.
"""

APP_NAME = "HappyMeasure"
PACKAGE_NAME = "happymeasure"
LEGACY_PACKAGE_NAME = "keith_ivt"
APP_CODENAME = "1.2 beta"
VERSION = "1.2b1"
__version__ = VERSION
RELEASE_STAGE = "beta"
__release_stage__ = RELEASE_STAGE
BUILD_NOTE = (
    "Post-1.2b development build; public v1.2b remains frozen at its published tag "
    "and release artifacts."
)
__build_note__ = BUILD_NOTE
