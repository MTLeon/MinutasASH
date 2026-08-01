from __future__ import annotations

"""Identidad inmutable del producto Minutas ASH 2.3.5."""

APP_NAME = "Minutas ASH"
APP_VERSION = "2.3.5"
RELEASE_SEQUENCE = 2_003_005
RELEASE_CHANNEL = "stable"
LEGACY_PREDECESSOR = "2.3.4"
ANALYSIS_PIPELINE_VERSION = "2.2"
DATABASE_SCHEMA_VERSION = 6


def display_version() -> str:
    return APP_VERSION
