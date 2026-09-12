from __future__ import annotations

import numpy as np
import pytest

from map_reconstruction.processing import MapProcessingConfig, ValueTransform, process_map


def test_custom_processing_converts_generated_inf_to_nan_with_warning() -> None:
    with np.errstate(divide="ignore", invalid="ignore"):
        processed = process_map(
            np.asarray([[0.0, 2.0]]),
            MapProcessingConfig(transform=ValueTransform.CUSTOM, custom_expression="1 / x"),
        )

    assert np.isnan(processed.values[0, 0])
    assert processed.values[0, 1] == pytest.approx(0.5)
    assert any("non-finite" in warning for warning in processed.warnings)
