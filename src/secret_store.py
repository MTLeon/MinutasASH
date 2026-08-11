from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Final

_TARGET_PREFIX: Final[str] = "ASH.MinutasASH"
_CRED_TYPE_GENERIC: Final[int] = 1
_CRED_PERSIST_LOCAL_MACHINE: Final[int] = 2


class SecretStoreError(RuntimeError):
    pass


def credential_target(provider_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in provider_id.strip())
    if not safe:
        raise ValueError("El identificador del proveedor no puede quedar vacío.")
    return f"{_TARGET_PREFIX}.{safe}.ApiKey"


def environment_variable(provider_id: str) -> str:
    return f"MINUTAS_ASH_{provider_id.upper().replace('-', '_')}_API_KEY"


if os.name == "nt":

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    _advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    _CredWriteW = _advapi32.CredWriteW
    _CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    _CredWriteW.restype = wintypes.BOOL

    _CredReadW = _advapi32.CredReadW
    _CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
    ]
    _CredReadW.restype = wintypes.BOOL

    _CredDeleteW = _advapi32.CredDeleteW
    _CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    _CredDeleteW.restype = wintypes.BOOL

    _CredFree = _advapi32.CredFree
    _CredFree.argtypes = [ctypes.c_void_p]
    _CredFree.restype = None


def _raise_windows_error(action: str) -> None:
    code = ctypes.get_last_error()
    raise SecretStoreError(f"No fue posible {action} la credencial de Windows. Código: {code}.")


def set_secret(provider_id: str, secret: str) -> None:
    secret = secret.strip()
    if not secret:
        raise ValueError("La credencial no puede quedar vacía.")
    if os.name != "nt":
        raise SecretStoreError(
            "El almacenamiento seguro de credenciales está disponible en Windows."
        )

    target = credential_target(provider_id)
    blob = secret.encode("utf-16-le")
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    credential = CREDENTIALW()
    credential.Type = _CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = "Minutas ASH"
    if not _CredWriteW(ctypes.byref(credential), 0):
        _raise_windows_error("guardar")


def get_secret(provider_id: str) -> str | None:
    env_value = os.getenv(environment_variable(provider_id), "").strip()
    if env_value:
        return env_value
    if os.name != "nt":
        return None

    target = credential_target(provider_id)
    pointer = ctypes.POINTER(CREDENTIALW)()
    if not _CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        code = ctypes.get_last_error()
        if code == 1168:  # ERROR_NOT_FOUND
            return None
        _raise_windows_error("leer")
    try:
        credential = pointer.contents
        if not credential.CredentialBlob or not credential.CredentialBlobSize:
            return None
        raw = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return raw.decode("utf-16-le")
    finally:
        _CredFree(pointer)


def delete_secret(provider_id: str) -> bool:
    if os.name != "nt":
        return False
    target = credential_target(provider_id)
    if _CredDeleteW(target, _CRED_TYPE_GENERIC, 0):
        return True
    code = ctypes.get_last_error()
    if code == 1168:
        return False
    _raise_windows_error("eliminar")
    return False


def has_secret(provider_id: str) -> bool:
    try:
        return bool(get_secret(provider_id))
    except SecretStoreError:
        return False
