from __future__ import annotations

GIB = 1024**3
MAX_INITIAL_FREE_SPACE = 7 * GIB
MODEL_ONLY_FREE_SPACE = 6 * GIB
READY_FREE_SPACE = 512 * 1024**2


def local_runtime_required(config: dict) -> bool:
    provider = str(config.get("processing_provider", "ollama_local"))
    return provider == "ollama_local" or bool(config.get("fallback_to_local", True))


def required_free_space_bytes(
    config: dict,
    *,
    api_ready: bool,
    model_installed: bool,
) -> int:
    if not local_runtime_required(config):
        return 0
    if model_installed:
        return READY_FREE_SPACE
    configured = int(config.get("minimum_free_space_bytes", MAX_INITIAL_FREE_SPACE))
    initial = min(configured, MAX_INITIAL_FREE_SPACE)
    return min(initial, MODEL_ONLY_FREE_SPACE) if api_ready else initial
