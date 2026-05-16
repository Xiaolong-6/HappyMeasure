"""Public HappyMeasure package namespace.

This package provides the user-facing import and command namespace.  The
implementation still lives under ``keith_ivt`` for this alpha cycle; imports
from ``keith_ivt`` remain supported as a legacy compatibility path.
"""

from __future__ import annotations

import sys

from keith_ivt import version as version
from keith_ivt.version import APP_NAME, LEGACY_PACKAGE_NAME, PACKAGE_NAME, VERSION, __version__

# Make ``import happymeasure.version`` work while keeping a single version source.
sys.modules[__name__ + ".version"] = version

__all__ = [
    "APP_NAME",
    "PACKAGE_NAME",
    "LEGACY_PACKAGE_NAME",
    "VERSION",
    "__version__",
    "version",
]
