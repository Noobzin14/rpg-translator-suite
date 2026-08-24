"""Qwen Translator Adapter for RPG Translator Suite.

This module provides a concrete implementation of the Translator interface
using Qwen-compatible HTTP APIs (OpenAI Chat Completions format).

Configuration is done via environment variables or explicit parameters:
- QWEN_API_KEY: API key for authentication (required)
- QWEN_BASE_URL: Base URL for the API endpoint (optional, defaults to a generic endpoint)
- QWEN_MODEL: Model identifier to use (optional, defaults to "qwen-coder-plus")
- QWEN_TIMEOUT: Request timeout in seconds (optional, defaults to 30)
- QWEN_MAX_RETRIES: Maximum number of retry attempts (optional, defaults to 3)
- QWEN_RETRY_BACKOFF: Backoff multiplier for retries (optional, defaults to 2.0)
- QWEN_RATE_LIMIT: Maximum requests per minute (optional, defaults to 60)

This adapter belongs to the services layer, NOT the core.
The core remains engine-independent and knows nothing about this implementation.
"""

from __future__ import annotations

import os
import time
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
        max_retries: Maximum number of retry attempts for transient errors.
        retry_backoff: Backoff multiplier for exponential backoff.
        rate_limit: Maximum requests per minute (rate limiting).
    """

    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-coder-plus"
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 2.0
    rate_limit: int = 60  # requests per minute

    @classmethod
    def from_env(cls) -> QwenTranslatorConfig:
        """Create configuration from environment variables.

        Environment variables:
        - QWEN_API_KEY: Required. The API key for authentication.
        - QWEN_BASE_URL: Optional. Defaults to DashScope compatible endpoint.
        - QWEN_MODEL: Optional. Defaults to "qwen-coder-plus".
        - QWEN_TIMEOUT: Optional. Defaults to 30.0 seconds.
        - QWEN_MAX_RETRIES: Optional. Defaults to 3.
        - QWEN_RETRY_BACKOFF: Optional. Defaults to 2.0.
        - QWEN_RATE_LIMIT: Optional. Defaults to 60 requests per minute.

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
        max_retries_str = os.environ.get("QWEN_MAX_RETRIES", "3")
        retry_backoff_str = os.environ.get("QWEN_RETRY_BACKOFF", "2.0")
        rate_limit_str = os.environ.get("QWEN_RATE_LIMIT", "60")

        try:
            timeout = float(timeout_str)
        except ValueError:
            timeout = 30.0

        try:
            max_retries = int(max_retries_str)
        except ValueError:
            max_retries = 3

        try:
            retry_backoff = float(retry_backoff_str)
        except ValueError:
            retry_backoff = 2.0

        try:
            rate_limit = int(rate_limit_str)
        except ValueError:
            rate_limit = 60

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            rate_limit=rate_limit,
        )


class QwenTranslator(Translator):
    """Concrete Translator implementation using Qwen-compatible HTTP APIs.

    This translator sends translation requests to a Qwen-compatible endpoint
    using the OpenAI Chat Completions format. It handles:
    - Configuration via environment variables or explicit parameters
    - HTTP communication with proper error handling
    - Retry with exponential backoff for transient errors
    - Rate limiting to avoid API throttling
    - Conversion of API responses to TranslationResult
    - Proper error classification and issue reporting

    Retry policy:
    - Retries are performed for transient errors only:
      - HTTP 5xx (server errors)
      - HTTP 429 (rate limit, respects Retry-After header)
      - Timeout exceptions
      - Connection errors
    - No retry for permanent errors:
      - HTTP 401 (authentication failed)
      - HTTP 403 (forbidden)
      - HTTP 404 (not found)
      - Invalid request format
    - Maximum retries: configured via max_retries (default: 3)
    - Backoff: exponential with base * (multiplier ^ attempt)

    Rate limiting:
    - Tracks request timestamps
    - Enforces maximum requests per minute
    - Waits if rate limit would be exceeded

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
        
        # Rate limiting: track request timestamps
        self._request_timestamps: list[float] = []

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
            - Retry with exponential backoff for transient errors.
            - Rate limiting is applied before each request.
        """
        # Apply rate limiting before making the request
        self._enforce_rate_limit()
        
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

        # Execute with retry logic
        return self._execute_with_retry(entry, headers, request_body)

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

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting by waiting if necessary.
        
        This method ensures that no more than config.rate_limit requests
        are made per minute by tracking request timestamps and waiting
        when the limit would be exceeded.
        """
        now = time.time()
        window_start = now - 60.0  # 1-minute sliding window
        
        # Remove timestamps outside the current window
        self._request_timestamps = [
            ts for ts in self._request_timestamps 
            if ts > window_start
        ]
        
        # Check if we've hit the rate limit
        if len(self._request_timestamps) >= self._config.rate_limit:
            # Calculate how long to wait until oldest request expires
            oldest = min(self._request_timestamps)
            wait_time = (oldest + 60.0) - now
            if wait_time > 0:
                time.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                window_start = now - 60.0
                self._request_timestamps = [
                    ts for ts in self._request_timestamps 
                    if ts > window_start
                ]
        
        # Record this request
        self._request_timestamps.append(time.time())

    def _execute_with_retry(
        self,
        entry: TranslationEntry,
        headers: dict[str, str],
        request_body: dict[str, Any],
    ) -> TranslationResult:
        """Execute API request with retry logic for transient errors.
        
        Args:
            entry: The translation entry.
            headers: HTTP headers for the request.
            request_body: Request body dictionary.
            
        Returns:
            TranslationResult with success or failure information.
        """
        last_error_result: TranslationResult | None = None
        
        for attempt in range(self._config.max_retries + 1):
            try:
                response = self._client.post(
                    f"{self._config.base_url}/chat/completions",
                    headers=headers,
                    json=request_body,
                )
                
                # Handle HTTP errors
                if response.status_code >= 500:
                    # Server error - retryable
                    if attempt < self._config.max_retries:
                        self._wait_for_retry(attempt, response.headers)
                        continue
                    return self._create_failed_result(
                        entry,
                        "api_server_error",
                        f"API server error (HTTP {response.status_code}). Please try again later.",
                    )
                
                if response.status_code == 429:
                    # Rate limit - always retry with Retry-After if available
                    if attempt < self._config.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        self._wait_for_retry(attempt, response.headers, retry_after)
                        continue
                    return self._create_failed_result(
                        entry,
                        "rate_limit_exceeded",
                        "Rate limit exceeded. Please wait before making more requests.",
                    )
                
                # Permanent errors - do not retry
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
                
                # Success - record the request timestamp for rate limiting
                self._request_timestamps.append(time.time())
                
                return TranslationResult(
                    entry_id=entry.id,
                    status=TranslationStatus.TRANSLATED,
                    original_text=entry.original_text,
                    translated_text=translated_text,
                    translator=self.translator_id,
                )
                
            except httpx.TimeoutException:
                if attempt < self._config.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                return self._create_failed_result(
                    entry,
                    "request_timeout",
                    f"Request timed out after {self._config.timeout} seconds.",
                )
                
            except httpx.ConnectError:
                if attempt < self._config.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                return self._create_failed_result(
                    entry,
                    "connection_failed",
                    "Failed to connect to the API. Please check your network connection and base URL.",
                )
                
            except httpx.RequestError as exc:
                if attempt < self._config.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                return self._create_failed_result(
                    entry,
                    "request_failed",
                    "Request failed due to a network error.",
                )
                
            except Exception as exc:
                if attempt < self._config.max_retries:
                    self._wait_for_retry(attempt)
                    continue
                return self._create_failed_result(
                    entry,
                    "unexpected_error",
                    f"An unexpected error occurred: {type(exc).__name__}",
                )
        
        # Should not reach here, but just in case
        if last_error_result:
            return last_error_result
        return self._create_failed_result(
            entry,
            "max_retries_exceeded",
            f"Maximum retries ({self._config.max_retries}) exceeded.",
        )

    def _wait_for_retry(
        self,
        attempt: int,
        response_headers: httpx.Headers | None = None,
        retry_after: str | None = None,
    ) -> None:
        """Wait before retrying using exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed).
            response_headers: Optional HTTP response headers.
            retry_after: Optional Retry-After header value.
        """
        # If Retry-After header is present, use it
        if retry_after:
            try:
                wait_time = float(retry_after)
                time.sleep(wait_time)
                return
            except (ValueError, TypeError):
                pass  # Fall through to exponential backoff
        
        # Exponential backoff: base * (multiplier ^ attempt)
        wait_time = 1.0 * (self._config.retry_backoff ** attempt)
        time.sleep(wait_time)
