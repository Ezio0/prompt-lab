"""DeepEval-compatible custom model for non-OpenAI LLM providers."""

from typing import Any

# deepeval is an optional dependency; import lazily
try:
    from deepeval.models import DeepEvalBaseLLM
    _DEEPEVAL_AVAILABLE = True
except ImportError:
    _DEEPEVAL_AVAILABLE = False
    DeepEvalBaseLLM = object  # type: ignore[assignment, misc]


class CustomModel(DeepEvalBaseLLM):
    """Wrap an OpenAI-compatible API (DeepSeek, vLLM, etc.) for DeepEval.

    DeepEval defaults to the OpenAI endpoint. For non-OpenAI providers,
    create a DeepEvalBaseLLM subclass that points to the correct base_url.
    """

    def __init__(self, model: str, base_url: str, api_key: str) -> None:
        if not _DEEPEVAL_AVAILABLE:
            raise ImportError(
                "DeepEval is not installed. Install with: pip install prompt-lab[eval]"
            )
        self._model_name = model
        self._base_url = base_url
        self._api_key = api_key

    def load_model(self) -> Any:
        from openai import OpenAI

        return OpenAI(base_url=self._base_url, api_key=self._api_key)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        client = self.load_model()
        response = client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content or ""

    def a_generate(self, prompt: str, **kwargs: Any) -> Any:
        """Async generation — delegates to sync for simplicity."""
        return self.generate(prompt, **kwargs)

    def get_model_name(self) -> str:
        return self._model_name


def is_deepeval_available() -> bool:
    """Check if DeepEval is installed and importable."""
    return _DEEPEVAL_AVAILABLE
