"""Qwen Translator Adapter for RPG Translator Suite.

This module provides a concrete implementation of the Translator interface
using Qwen-compatible HTTP APIs (OpenAI Chat Completions format).

Configuration is done via environment variables or explicit parameters:
- QWEN_API_KEY: API key for authentication (required)
- QWEN_BASE_URL: Base URL for the API endpoint (optional, defaults to a generic endpoint)
- QWEN_MODEL: Model identifier to use (optional, defaults to "qwen-coder-plus")
- QWEN_TIMEOUT: Request timeout in seconds (optional, defaults to 30)

This adapter belongs to the services layer, NOT the core.
The core remains engine-independent and knows nothing about this implementation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.translation import (
    TranslationEntry,
    TranslationIssue,
    TranslationIssueSeverity,
    TranslationResult,
    TranslationStatus,
    Translator,
)


@dataclass(frozen=True)
class QwenTranslatorConfig:
    """Configuration for QwenTranslator.

    Attributes:
        api_key: The API key for authentication. Must not be None.
        base_url: The base URL for the API endpoint.
        model: The model identifier to use for translations.
        timeout: Request timeout in seconds.
    """

    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-coder-plus"
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> QwenTranslatorConfig:
        """Create configuration from environment variables.

        Environment variables:
        - QWEN_API_KEY: Required. The API key for authentication.
        - QWEN_BASE_URL: Optional. Defaults to DashScope compatible endpoint.
        - QWEN_MODEL: Optional. Defaults to "qwen-coder-plus".
        - QWEN_TIMEOUT: Optional. Defaults to 30.0 seconds.

        Returns:
            A QwenTranslatorConfig instance.

        Raises:
            ValueError: If QWEN_API_KEY is not set.
        """
        api_key = os.environ.get("QWEN_API_KEY")
        if not api_key:
            raise ValueError(
                "QWEN_API_KEY environment variable is required. "
                "Please set it to your Qwen API key."
            )

        base_url = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        model = os.environ.get("QWEN_MODEL", "qwen-coder-plus")
        timeout_str = os.environ.get("QWEN_TIMEOUT", "30.0")

        try:
            timeout = float(timeout_str)
        except ValueError:
            timeout = 30.0

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
        )


class QwenTranslator(Translator):
    """Concrete Translator implementation using Qwen-compatible HTTP APIs.

    This translator sends translation requests to a Qwen-compatible endpoint
    using the OpenAI Chat Completions format. It handles:
    - Configuration via environment variables or explicit parameters
    - HTTP communication with proper error handling
    - Conversion of API responses to TranslationResult
    - Proper error classification and issue reporting

    Security considerations:
    - API key is never logged or included in error messages
    - API key is only used in the Authorization header
    - No credentials are stored in code or tests
    """

    def __init__(
        self,
        config: QwenTranslatorConfig | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize the QwenTranslator.

        Args:
            config: Optional configuration object. If provided, other parameters
                are ignored except for explicit overrides.
            api_key: Optional API key override.
            base_url: Optional base URL override.
            model: Optional model override.
            timeout: Optional timeout override.

        Raises:
            ValueError: If no API key is provided (neither in config nor as parameter).
        """
        if config is None:
            # Build config from parameters or environment
            if api_key is None:
                # Try to get from environment
                env_key = os.environ.get("QWEN_API_KEY")
                if not env_key:
                    raise ValueError(
                        "API key is required. Provide it via 'api_key' parameter "
                        "or set QWEN_API_KEY environment variable."
                    )
                api_key = env_key

            config = QwenTranslatorConfig(
                api_key=api_key,
                base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                model=model or "qwen-coder-plus",
                timeout=timeout if timeout is not None else 30.0,
            )
        else:
            # Apply overrides if provided
            override_kwargs: dict[str, Any] = {}
            if api_key is not None:
                override_kwargs["api_key"] = api_key
            if base_url is not None:
                override_kwargs["base_url"] = base_url
            if model is not None:
                override_kwargs["model"] = model
            if timeout is not None:
                override_kwargs["timeout"] = timeout

            if override_kwargs:
                config = dataclass_replace(config, **override_kwargs)

        self._config = config
        self._client = httpx.Client(timeout=self._config.timeout)

    def __del__(self) -> None:
        """Cleanup HTTP client on destruction."""
        if hasattr(self, "_client"):
            try:
                self._client.close()
            except Exception:
                pass  # Ignore cleanup errors

    @property
    def translator_id(self) -> str:
        """Return the unique identifier for this translator."""
        return "qwen"

    @property
    def config(self) -> QwenTranslatorConfig:
        """Return the current configuration (read-only)."""
        return self._config

    def translate(self, entry: TranslationEntry) -> TranslationResult:
        """Translate a single entry using the Qwen API.

        Args:
            entry: The translation entry to process.

        Returns:
            A TranslationResult containing the translation outcome.

        Notes:
            - The original entry is not modified.
            - API key is never exposed in errors or logs.
            - HTTP errors are converted to FAILED status with appropriate issues.
        """
        # Build the prompt for translation
        system_prompt = (
            "You are a professional translator. Translate the following text "
            "accurately and naturally. Return ONLY the translated text, without "
            "any explanations, comments, markdown formatting, or additional content."
        )

        # Build user message with context if available
        user_message_parts = []

        if entry.context:
            user_message_parts.append(f"Context: {entry.context}")

        if entry.metadata:
            metadata_str = ", ".join(f"{k}={v}" for k, v in entry.metadata.items() if v is not None)
            if metadata_str:
                user_message_parts.append(f"Metadata: {metadata_str}")

        user_message_parts.append(f"Text to translate: {entry.original_text}")

        user_message = "\n".join(user_message_parts)

        # Build the request body (OpenAI Chat Completions format)
        request_body = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,  # Low temperature for more deterministic output
            "max_tokens": 4096,
        }

        # Set up headers
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self._client.post(
                f"{self._config.base_url}/chat/completions",
                headers=headers,
                json=request_body,
            )

            # Handle HTTP errors
            if response.status_code >= 500:
                return self._create_failed_result(
                    entry,
                    "api_server_error",
                    f"API server error (HTTP {response.status_code}). Please try again later.",
                )

            if response.status_code == 429:
                return self._create_failed_result(
                    entry,
                    "rate_limit_exceeded",
                    "Rate limit exceeded. Please wait before making more requests.",
                )

            if response.status_code == 401:
                return self._create_failed_result(
                    entry,
                    "authentication_failed",
                    "Authentication failed. Please check your API key configuration.",
                )

            if response.status_code == 403:
                return self._create_failed_result(
                    entry,
                    "access_forbidden",
                    "Access forbidden. Your API key may not have permission for this operation.",
                )

            if response.status_code == 404:
                return self._create_failed_result(
                    entry,
                    "endpoint_not_found",
                    "API endpoint not found. Please check your base URL configuration.",
                )

            if response.status_code >= 400:
                return self._create_failed_result(
                    entry,
                    "api_client_error",
                    f"API request failed (HTTP {response.status_code}).",
                )

            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                return self._create_failed_result(
                    entry,
                    "invalid_response_format",
                    "Received invalid JSON response from API.",
                )

            # Extract translated text
            translated_text = self._extract_translated_text(response_data)

            if translated_text is None:
                return self._create_failed_result(
                    entry,
                    "empty_translation",
                    "API returned no translation text.",
                )

            if not translated_text.strip():
                return self._create_failed_result(
                    entry,
                    "empty_translation",
                    "API returned empty translation text.",
                )

            # Success
            return TranslationResult(
                entry_id=entry.id,
                status=TranslationStatus.TRANSLATED,
                original_text=entry.original_text,
                translated_text=translated_text,
                translator=self.translator_id,
            )

        except httpx.TimeoutException:
            return self._create_failed_result(
                entry,
                "request_timeout",
                f"Request timed out after {self._config.timeout} seconds.",
            )

        except httpx.ConnectError:
            return self._create_failed_result(
                entry,
                "connection_failed",
                "Failed to connect to the API. Please check your network connection and base URL.",
            )

        except httpx.RequestError as exc:
            # Generic request error - don't expose internal details
            return self._create_failed_result(
                entry,
                "request_failed",
                "Request failed due to a network error.",
            )

        except Exception as exc:
            # Unexpected error
            return self._create_failed_result(
                entry,
                "unexpected_error",
                f"An unexpected error occurred: {type(exc).__name__}",
            )

    def _extract_translated_text(self, response_data: dict[str, Any]) -> str | None:
        """Extract translated text from API response.

        Args:
            response_data: The parsed JSON response from the API.

        Returns:
            The extracted translated text, or None if extraction fails.
        """
        try:
            choices = response_data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                return None

            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                return None

            message = first_choice.get("message")
            if not isinstance(message, dict):
                return None

            content = message.get("content")
            if not isinstance(content, str):
                return None

            return content.strip()

        except (KeyError, TypeError, IndexError):
            return None

    def _create_failed_result(
        self,
        entry: TranslationEntry,
        code: str,
        message: str,
    ) -> TranslationResult:
        """Create a FAILED TranslationResult with an issue.

        Args:
            entry: The original translation entry.
            code: The issue code.
            message: The human-readable error message.

        Returns:
            A TranslationResult with FAILED status.
        """
        issue = TranslationIssue(
            severity=TranslationIssueSeverity.ERROR,
            code=code,
            message=message,
            entry_id=entry.id,
            source_file=entry.source_file,
        )

        return TranslationResult(
            entry_id=entry.id,
            status=TranslationStatus.FAILED,
            original_text=entry.original_text,
            translated_text=None,
            translator=self.translator_id,
            issues=(issue,),
        )


def dataclass_replace(dc: Any, **kwargs: Any) -> Any:
    """Replace fields in a frozen dataclass.

    This is a helper function to work around frozen dataclasses.

    Args:
        dc: The dataclass instance.
        **kwargs: Field names and new values.

    Returns:
        A new dataclass instance with replaced fields.
    """
    import dataclasses

    if not dataclasses.is_dataclass(dc):
        raise TypeError("Expected a dataclass instance")

    changes = {field.name: getattr(dc, field.name) for field in dataclasses.fields(dc)}
    changes.update(kwargs)
    return type(dc)(**changes)
