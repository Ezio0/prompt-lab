import httpx
import pytest

from prompt_lab.core.config import ProviderConfig
from prompt_lab.core.provider import (
    Provider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


def config() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://provider.test/v1",
        api_key_env="TEST_KEY",
        api_key="secret",
        model="test-model",
        default_params={"max_tokens": 64, "temperature": 0.1, "thinking": "disabled"},
    )


def transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_call_posts_openai_compatible_payload_and_returns_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://provider.test/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer secret"
        body = json_body(request)
        assert body["model"] == "override-model"
        assert body["max_tokens"] == 10
        assert body["thinking"] == {"type": "enabled"}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4},
            },
        )

    response = await Provider(config(), transport=transport(handler)).call(
        "Prompt", model="override-model", max_tokens=10, thinking="enabled"
    )

    assert (response.content, response.prompt_tokens, response.completion_tokens) == ("Hello", 3, 4)
    assert response.finish_reason == "stop"


@pytest.mark.asyncio
async def test_call_maps_401_to_non_retryable_auth_error():
    with pytest.raises(ProviderAuthError) as error:
        await Provider(config(), transport=transport(lambda _: httpx.Response(401))).call("Prompt")

    assert error.value.retryable is False


@pytest.mark.asyncio
async def test_call_maps_429_to_retryable_rate_limit_error():
    with pytest.raises(ProviderRateLimitError) as error:
        await Provider(config(), transport=transport(lambda _: httpx.Response(429))).call("Prompt")

    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_call_maps_timeout_to_retryable_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ProviderTimeoutError) as error:
        await Provider(config(), transport=transport(handler)).call("Prompt")

    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_call_maps_5xx_to_retryable_provider_error():
    with pytest.raises(ProviderError) as error:
        await Provider(config(), transport=transport(lambda _: httpx.Response(503))).call("Prompt")

    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_call_preserves_empty_content():
    response = await Provider(
        config(),
        transport=transport(
            lambda _: httpx.Response(
                200,
                json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {}},
            )
        ),
    ).call("Prompt")

    assert response.content == ""
    assert response.prompt_tokens == 0
    assert response.finish_reason == "length"


def json_body(request: httpx.Request) -> dict:
    import json

    return json.loads(request.content)
