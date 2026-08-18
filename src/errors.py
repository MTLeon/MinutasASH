from __future__ import annotations


class AppError(Exception):
    """Base error with separate technical and user-facing descriptions."""

    user_message = "No fue posible completar la operación."

    def __init__(self, technical_detail: str = "", *, user_message: str | None = None) -> None:
        self.technical_detail = technical_detail
        self.user_message = user_message or self.user_message
        super().__init__(technical_detail or self.user_message)


class ConfigurationError(AppError):
    user_message = "La configuración de la aplicación no es válida."


class ProcessingError(AppError):
    user_message = "No fue posible procesar la reunión."


class StorageError(AppError):
    user_message = "No fue posible guardar la información."
