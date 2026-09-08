from __future__ import annotations

import numpy as np

from map_reconstruction.methods.dual_offset import apply_scan_orientation
from map_reconstruction.models import ScanPattern

VALUES = np.asarray([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
COUNTS = VALUES.copy()


def test_same_direction_ltr_and_rtl():
    ltr, _ = apply_scan_orientation(VALUES, COUNTS, ScanPattern.SAME_DIRECTION, True)
    rtl, _ = apply_scan_orientation(VALUES, COUNTS, ScanPattern.SAME_DIRECTION, False)

    np.testing.assert_array_equal(ltr, VALUES)
    np.testing.assert_array_equal(rtl, np.fliplr(VALUES))


def test_serpentine_orientation_parity():
    ltr, _ = apply_scan_orientation(VALUES, COUNTS, ScanPattern.SERPENTINE, True)
    rtl, _ = apply_scan_orientation(VALUES, COUNTS, ScanPattern.SERPENTINE, False)

    np.testing.assert_array_equal(ltr, [[1, 2, 3], [6, 5, 4], [7, 8, 9]])
    np.testing.assert_array_equal(rtl, [[3, 2, 1], [4, 5, 6], [9, 8, 7]])
