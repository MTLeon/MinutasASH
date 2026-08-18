from src.storage_policy import GIB, required_free_space_bytes


def test_remote_provider_without_local_fallback_needs_no_local_install_space():
    config = {"processing_provider": "openai", "fallback_to_local": False}
    assert required_free_space_bytes(config, api_ready=False, model_installed=False) == 0


def test_legacy_twelve_gib_requirement_is_capped_for_initial_install():
    config = {"minimum_free_space_bytes": 12 * GIB}
    assert required_free_space_bytes(config, api_ready=False, model_installed=False) == 7 * GIB


def test_existing_runtime_only_reserves_space_for_model():
    assert required_free_space_bytes({}, api_ready=True, model_installed=False) == 6 * GIB


def test_installed_model_only_needs_operational_reserve():
    assert required_free_space_bytes({}, api_ready=True, model_installed=True) < GIB
