from __future__ import annotations

from scripts.runtime_config import load_runtime_config, render_generated_module


def test_runtime_config_renders_loader_constants() -> None:
    config = load_runtime_config()
    rendered = render_generated_module(config)

    assert "LINUX_LIBRARIES = (" in rendered
    assert "WINDOWS_LIBRARIES = (" in rendered
    assert "MACOS_LIBRARY_ALIASES = {" in rendered
    assert config["linux"]["preload"][0] in rendered
