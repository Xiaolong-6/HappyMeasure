"""PyInstaller entry point for the standalone Map Reconstruction app.

This file is intentionally tiny: keeping the executable entry point separate
from package internals makes PyInstaller builds more predictable and avoids
running package-level code during analysis.
"""

from map_reconstruction.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
