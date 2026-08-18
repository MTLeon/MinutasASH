"""Identidad inmutable del producto Minutas ASH 2.3.7."""

from __future__ import annotations

APP_NAME = "Minutas ASH"
APP_VERSION = "2.3.7"
RELEASE_SEQUENCE = 2_003_007
RELEASE_CHANNEL = "stable"
LEGACY_PREDECESSOR = "2.3.3"
ANALYSIS_PIPELINE_VERSION = "2.1"
DATABASE_SCHEMA_VERSION = 8


def display_version() -> str:
    return APP_VERSION
