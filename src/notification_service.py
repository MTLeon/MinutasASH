"""Notificación local no bloqueante para procesos terminados."""

from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path


def _powershell_encoded(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def notify_local(title: str, message: str, path: str | Path | None = None) -> bool:
    if sys.platform != "win32":
        return False
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_message = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    destination = str(Path(path).resolve()) if path else ""
    safe_destination = destination.replace("'", "''")
    script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$text = $xml.GetElementsByTagName('text')
$text.Item(0).AppendChild($xml.CreateTextNode('{safe_title}')) > $null
$text.Item(1).AppendChild($xml.CreateTextNode('{safe_message}')) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Minutas ASH').Show($toast)
"""
    if destination:
        script += (
            f"if (Test-Path -LiteralPath '{safe_destination}') "
            f"{{ Write-Output '{safe_destination}' }}\n"
        )
    try:
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-EncodedCommand",
                _powershell_encoded(script),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return False
    return True
