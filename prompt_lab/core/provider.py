"""OpenAI-compatible provider adapter."""

from typing import Any

import httpx

from prompt_lab.core.config import ProviderConfig
from prompt_lab.core.models import ProviderResponse


class ProviderError(RuntimeError):
    """A provider request failure with retry metadata."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class ProviderAuthError(ProviderError):
    """An authentication failure that should not be retried."""

    def __init__(self) -> None:
        super().__init__("E_PROVIDER_AUTH: provider authentication failed", retryable=False)


class ProviderRateLimitError(ProviderError):
    """A rate-limit failure that may succeed after waiting."""

    def __init__(self) -> None:
        super().__init__("E_PROVIDER_RATE_LIMIT: provider rate limit reached", retryable=True)


class ProviderTimeoutError(ProviderError):
    """A timeout or connection failure that may be retried."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"E_PROVIDER_TIMEOUT: {detail}", retryable=True)


class Provider:
    """Call an OpenAI-compatible chat-completions endpoint."""

    def __init__(self, config: ProviderConfig, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.config = config
        self.transport = transport

    async def call(self, prompt: str, **params: Any) -> ProviderResponse:
        """Send one prompt and normalize its completion data."""
        request_params = dict(self.config.default_params)
        request_params.update(params)
        model = request_params.pop("model", self.config.model)
        timeout = request_params.pop("timeout_seconds", 60.0)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **{key: value for key, value in request_params.items() if value is not None},
        }
        url = f"{self.config.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self.transport) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError(str(error)) from error
        except httpx.RequestError as error:
            raise ProviderError(f"E_PROVIDER_REQUEST: {error}", retryable=True) from error

        if response.status_code == 401:
            raise ProviderAuthError()
        if response.status_code == 429:
            raise ProviderRateLimitError()
        if response.status_code >= 500:
            raise ProviderError(
                f"E_PROVIDER_HTTP: provider returned HTTP {response.status_code}", retryable=True
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"E_PROVIDER_HTTP: provider returned HTTP {response.status_code}", retryable=False
            )

        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"].get("content") or ""
            usage = data.get("usage") or {}
            return ProviderResponse(
                content=content,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                finish_reason=choice.get("finish_reason"),
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise ProviderError(f"E_PROVIDER_RESPONSE: malformed provider response: {error}", retryable=False) from error
