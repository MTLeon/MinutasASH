"""Auditoría determinista de geometrías y escalas soportadas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.appearance import effective_scale
from src.ui_state import normalized_geometry

RESOLUTIONS = ((1280, 720), (1366, 768), (1920, 1080), (2560, 1440), (3840, 2160))
REQUESTED_SCALES = (0.8, 1.0, 1.1, 1.25, 1.5)
WINDOWS = {
    "main": ("1180x790", (1000, 700)),
    "item_dialog": ("760x600", (650, 480)),
    "preferences": ("860x720", (720, 560)),
}


def audit_layouts() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for resolution in RESOLUTIONS:
        for requested in REQUESTED_SCALES:
            scale = effective_scale(requested, resolution)
            for name, (default, minimum) in WINDOWS.items():
                geometry = normalized_geometry(None, default, minimum, resolution)
                size = geometry.split("+", 1)[0]
                width, height = (int(value) for value in size.split("x"))
                passed = width <= resolution[0] and height <= resolution[1]
                row = {
                    "window": name,
                    "resolution": list(resolution),
                    "requested_scale": requested,
                    "effective_scale": scale,
                    "geometry": geometry,
                    "passed": passed,
                }
                cases.append(row)
                if not passed:
                    failures.append(row)
    return {
        "schema": "minutas-ash-layout-audit-v1",
        "cases": cases,
        "failures": failures,
        "passed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("salida/diagnostico/layouts.json"))
    args = parser.parse_args()
    report = audit_layouts()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(report["cases"]), "failures": len(report["failures"])}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
