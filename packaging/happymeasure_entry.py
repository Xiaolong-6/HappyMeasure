"""PyInstaller entry point for the HappyMeasure desktop app.

This file is intentionally tiny: keeping the executable entry point separate
from package internals makes PyInstaller builds more predictable and avoids
running package-level code during analysis.
"""

from keith_ivt.ui.simple_app import main


if __name__ == "__main__":
    main()
