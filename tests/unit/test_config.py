import pytest

from prompt_lab.core.config import Config, ConfigError


CONFIG = """
provider:
  base_url: https://example.test/v1
  api_key_env: TEST_PROMPT_LAB_KEY
  model: test-model
  default_params:
    max_tokens: 256
    temperature: 0.2
    thinking: disabled
run:
  timeout_seconds: 10
  concurrency: 2
"""


def test_load_returns_typed_config_and_reads_api_key(tmp_path, monkeypatch):
    (tmp_path / "prompt-lab.yaml").write_text(CONFIG, encoding="utf-8")
    monkeypatch.setenv("TEST_PROMPT_LAB_KEY", "secret")

    config = Config.load(tmp_path)

    assert config.provider.base_url == "https://example.test/v1"
    assert config.provider.api_key == "secret"
    assert config.provider.default_params["max_tokens"] == 256
    assert config.run.concurrency == 2


def test_load_rejects_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="E_CONFIG_INVALID"):
        Config.load(tmp_path)


def test_load_rejects_invalid_yaml(tmp_path):
    (tmp_path / "prompt-lab.yaml").write_text("provider: [", encoding="utf-8")

    with pytest.raises(ConfigError, match="E_CONFIG_INVALID"):
        Config.load(tmp_path)


def test_load_rejects_missing_api_key(tmp_path, monkeypatch):
    (tmp_path / "prompt-lab.yaml").write_text(CONFIG, encoding="utf-8")
    monkeypatch.delenv("TEST_PROMPT_LAB_KEY", raising=False)

    with pytest.raises(ConfigError, match="E_CONFIG_INVALID"):
        Config.load(tmp_path)
