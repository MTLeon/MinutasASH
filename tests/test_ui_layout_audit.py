from __future__ import annotations

from src.appearance import effective_scale
from src.ui_layout_audit import REQUESTED_SCALES, RESOLUTIONS, audit_layouts


def test_effective_scale_keeps_main_window_visible():
    for resolution in RESOLUTIONS:
        for requested in REQUESTED_SCALES:
            scale = effective_scale(requested, resolution)
            assert 1000 * scale <= resolution[0] + 0.001
            assert 700 * scale <= resolution[1] + 0.001
            assert 0.8 <= scale <= 1.5


def test_layout_matrix_has_no_offscreen_windows():
    report = audit_layouts()
    assert report["passed"] is True
    assert report["failures"] == []
    assert len(report["cases"]) == len(RESOLUTIONS) * len(REQUESTED_SCALES) * 3
