from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.updater import (
    UpdateInfo,
    check_github_release,
    check_manifest,
    download_update,
    is_newer_version,
    should_check_now,
    update_source_is_configured,
)


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.headers = {"content-length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int):
        return (
            self.payload[index : index + chunk_size]
            for index in range(0, len(self.payload), chunk_size)
        )


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_comparison(self):
        self.assertTrue(is_newer_version("5.2.0", "5.1.1"))
        self.assertFalse(is_newer_version("5.1.1", "5.1.1"))
        self.assertFalse(is_newer_version("5.1.0", "5.1.1"))
        self.assertTrue(is_newer_version("2.2.1", "2.2.0", 2002001, 2002000))
        self.assertFalse(is_newer_version("2.1.0", "2.2.0", 2001000, 2002000))

    def test_update_source_configuration(self):
        self.assertFalse(
            update_source_is_configured({"update_source": "manifest", "update_manifest_url": ""})
        )
        self.assertTrue(
            update_source_is_configured(
                {"update_source": "github", "github_owner": "ash", "github_repo": "minutas"}
            )
        )

    def test_startup_check_is_disabled_without_source(self):
        settings = {
            "update_enabled": True,
            "update_check_on_start": True,
            "update_source": "manifest",
            "update_manifest_url": "",
        }
        self.assertFalse(should_check_now(settings))

    @patch("src.updater._get_json")
    def test_manifest_parsing(self, get_json):
        get_json.return_value = {
            "version": "2.1.1",
            "release_sequence": 2001001,
            "installer_url": "https://updates.example/MinutasASH.exe",
            "sha256": "a" * 64,
            "release_notes": ["Corrección A", "Mejora B"],
        }
        info = check_manifest("https://updates.example/latest.json")
        self.assertEqual(info.version, "2.1.1")
        self.assertEqual(info.release_sequence, 2001001)
        self.assertIn("Corrección A", info.release_notes)

    @patch("src.updater._read_sha256_text", return_value="a" * 64)
    @patch("src.updater._get_json")
    def test_github_release_accepts_and_orders_installer_parts(self, get_json, _checksum):
        get_json.return_value = {
            "tag_name": "v2.3.5",
            "assets": [
                {
                    "name": "MinutasASH_Setup_2.3.5_Online.exe.part02",
                    "browser_download_url": "https://example/part02",
                },
                {
                    "name": "MinutasASH_Setup_2.3.5_Online_SHA256.txt",
                    "browser_download_url": "https://example/hash",
                },
                {
                    "name": "MinutasASH_Setup_2.3.5_Online.exe.part01",
                    "browser_download_url": "https://example/part01",
                },
            ],
        }
        info = check_github_release("MTLeon", "MinutasASH-Releases")
        self.assertEqual(info.version, "2.3.5")
        self.assertEqual(info.installer_parts, ("https://example/part01", "https://example/part02"))
        self.assertEqual(info.installer_url, "https://example/part01")

    @patch("src.updater.user_data_root")
    @patch("src.updater.requests.get")
    def test_download_reconstructs_parts_and_verifies_final_hash(self, get, data_root):
        parts = (b"primer-", b"segundo")
        get.side_effect = [_Response(part) for part in parts]
        with TemporaryDirectory() as temporary:
            data_root.return_value = Path(temporary)
            info = UpdateInfo(
                version="2.3.5",
                installer_url="https://example/MinutasASH_Setup_2.3.5.exe.part01",
                installer_parts=(
                    "https://example/MinutasASH_Setup_2.3.5.exe.part01",
                    "https://example/MinutasASH_Setup_2.3.5.exe.part02",
                ),
                sha256=hashlib.sha256(b"".join(parts)).hexdigest(),
                release_notes="",
            )
            messages: list[str] = []
            target = download_update(info, lambda _value, text: messages.append(text))
            self.assertEqual(target.name, "MinutasASH_Setup_2.3.5.exe")
            self.assertEqual(target.read_bytes(), b"".join(parts))
        self.assertEqual(get.call_count, 2)
        self.assertTrue(any("parte 1/2" in text for text in messages))
        self.assertTrue(any("parte 2/2" in text for text in messages))


if __name__ == "__main__":
    unittest.main()
