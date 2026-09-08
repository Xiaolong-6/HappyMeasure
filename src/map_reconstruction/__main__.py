from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconstruct a 2-D map from a HappyMeasure CSV.")
    parser.add_argument("path", nargs="?", type=Path, help="optional HappyMeasure single-v2 CSV")
    args = parser.parse_args(argv)
    try:
        from map_reconstruction.ui.main_window import run_app
    except ImportError as exc:
        print(
            "Map Reconstruction requires optional GUI dependencies.\n"
            'Install with: pip install -e ".[map]"\n'
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 2
    return run_app(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
