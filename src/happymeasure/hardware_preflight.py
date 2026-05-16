"""Public hardware preflight entry point for HappyMeasure."""

from __future__ import annotations

import sys

from keith_ivt.hardware_preflight import main


if __name__ == "__main__":
    sys.exit(main())
