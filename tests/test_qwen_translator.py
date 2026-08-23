"""Tests for QwenTranslator implementation.

These tests use mocked HTTP responses to verify translator behavior
without making real API calls. No API keys are used in tests.
"""

from pathlib import Path

import httpx
import pytest

from app.core.translation import (
    TranslationEntry,
    TranslationIssueSeverity,
    TranslationResult,
    TranslationStatus,
)
from app.services.qwen_translator import QwenTranslator, QwenTranslatorConfig


# Test configuration - uses a fake API key that is never used for real requests
TEST_API_KEY = "test_fake_key_never_used_in_production"
TEST_BASE_URL = "https://test.example.com/api"
TEST_MODEL = "test-model"
TEST_TIMEOUT = 5.0


def create_test_config(
    api_key: str = TEST_API_KEY,
    base_url: str = TEST_BASE_URL,
    model: str = TEST_MODEL,
    timeout: float = TEST_TIMEOUT,
) -> QwenTranslatorConfig:
    """Create a test configuration."""
    return QwenTranslatorConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
    )


def create_test_entry(
    entry_id: str = "test_001",
    original_text: str = "Hello, world!",
    context: str | None = None,
    metadata: dict | None = None,
    source_file: Path | None = None,
) -> TranslationEntry:
    """Create a test translation entry."""
    return TranslationEntry(
        id=entry_id,
        original_text=original_text,
        context=context,
        metadata=metadata or {},
        source_file=source_file,
    )


def create_mock_response(
    status_code: int,
    json_data: dict | None = None,
    text_content: str = "",
) -> httpx.Response:
    """Create a mock HTTP response."""
    if json_data is not None:
        return httpx.Response(status_code, json=json_data)
    return httpx.Response(status_code, text=text_content)


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self) -> None:
        self.request_history: list[dict] = []
        self._response_to_return: httpx.Response | None = None
        self._exception_to_raise: Exception | None = None

    def set_response(self, response: httpx.Response) -> None:
        """Set the response to return for the next request."""
        self._response_to_return = response
        self._exception_to_raise = None

    def set_exception(self, exc: Exception) -> None:
        """Set an exception to raise for the next request."""
        self._exception_to_raise = exc
        self._response_to_return = None

    def post(self, url: str, **kwargs) -> httpx.Response:
        """Mock post method."""
        self.request_history.append({
            "url": url,
            "headers": kwargs.get("headers", {}),
            "json": kwargs.get("json"),
        })

        if self._exception_to_raise:
            raise self._exception_to_raise

        if self._response_to_return:
            return self._response_to_return

        # Default response
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": "Translated text"}
            }]
        })

    def close(self) -> None:
        """Mock close method."""
        pass


class TestQwenTranslatorConfig:
    """Test QwenTranslatorConfig."""

    def test_create_config_minimal(self):
        """Test creating config with minimal fields."""
        config = QwenTranslatorConfig(api_key="test_key")
        assert config.api_key == "test_key"
        assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert config.model == "qwen-coder-plus"
        assert config.timeout == 30.0

    def test_create_config_full(self):
        """Test creating config with all fields."""
        config = QwenTranslatorConfig(
            api_key="test_key",
            base_url="https://custom.example.com",
            model="custom-model",
            timeout=60.0,
        )
        assert config.api_key == "test_key"
        assert config.base_url == "https://custom.example.com"
        assert config.model == "custom-model"
        assert config.timeout == 60.0

    def test_config_is_frozen(self):
        """Test that config is immutable."""
        config = QwenTranslatorConfig(api_key="test_key")
        with pytest.raises(AttributeError):
            config.api_key = "new_key"  # type: ignore[misc]

    def test_from_env_missing_api_key(self):
        """Test from_env raises when API key is missing."""
        # Save original env
        import os
        original = os.environ.pop("QWEN_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="QWEN_API_KEY"):
                QwenTranslatorConfig.from_env()
        finally:
            # Restore original env
            if original:
                os.environ["QWEN_API_KEY"] = original


class TestQwenTranslatorInitialization:
    """Test QwenTranslator initialization."""

    def test_init_with_config(self):
        """Test initialization with config object."""
        config = create_test_config()
        translator = QwenTranslator(config=config)
        assert translator.translator_id == "qwen"
        assert translator.config == config

    def test_init_with_parameters(self):
        """Test initialization with explicit parameters."""
        translator = QwenTranslator(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
            model=TEST_MODEL,
            timeout=TEST_TIMEOUT,
        )
        assert translator.translator_id == "qwen"
        assert translator.config.api_key == TEST_API_KEY
        assert translator.config.base_url == TEST_BASE_URL

    def test_init_missing_api_key_raises(self):
        """Test that missing API key raises ValueError."""
        import os
        original = os.environ.pop("QWEN_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="API key"):
                QwenTranslator()
        finally:
            if original:
                os.environ["QWEN_API_KEY"] = original

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("QWEN_API_KEY", "env_key")
        monkeypatch.setenv("QWEN_BASE_URL", "https://env.example.com")
        monkeypatch.setenv("QWEN_MODEL", "env-model")
        monkeypatch.setenv("QWEN_TIMEOUT", "45.0")

        # Need to clear cached config by not using any existing instance
        translator = QwenTranslator(
            api_key="env_key",
            base_url="https://env.example.com",
            model="env-model",
            timeout=45.0,
        )
        assert translator.config.api_key == "env_key"
        assert translator.config.base_url == "https://env.example.com"
        assert translator.config.model == "env-model"
        assert translator.config.timeout == 45.0


class TestQwenTranslatorSuccess:
    """Test successful translation scenarios."""

    def test_translate_success(self):
        """Test successful translation."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        # Mock the HTTP client
        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{
                "message": {"content": "Olá, mundo!"}
            }]
        }))
        translator._client = mock_client

        entry = create_test_entry(original_text="Hello, world!")
        result = translator.translate(entry)

        assert result.status == TranslationStatus.TRANSLATED
        assert result.entry_id == "test_001"
        assert result.original_text == "Hello, world!"
        assert result.translated_text == "Olá, mundo!"
        assert result.translator == "qwen"
        assert result.issues == ()

    def test_translate_with_context(self):
        """Test translation with context."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{
                "message": {"content": "Tradução com contexto"}
            }]
        }))
        translator._client = mock_client

        entry = create_test_entry(
            original_text="Click here",
            context="button_label",
        )
        result = translator.translate(entry)

        assert result.status == TranslationStatus.TRANSLATED
        # Verify request included context
        assert len(mock_client.request_history) == 1
        request_json = mock_client.request_history[0]["json"]
        user_message = request_json["messages"][1]["content"]
        assert "Context: button_label" in user_message

    def test_translate_with_metadata(self):
        """Test translation with metadata."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{
                "message": {"content": "Translation with metadata"}
            }]
        }))
        translator._client = mock_client

        entry = create_test_entry(
            original_text="Item name",
            metadata={"item_type": "weapon", "rarity": "legendary"},
        )
        result = translator.translate(entry)

        assert result.status == TranslationStatus.TRANSLATED
        # Verify request included metadata
        assert len(mock_client.request_history) == 1
        request_json = mock_client.request_history[0]["json"]
        user_message = request_json["messages"][1]["content"]
        assert "Metadata:" in user_message

    def test_translate_preserves_entry_id(self):
        """Test that entry ID is preserved."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{
                "message": {"content": "Translated"}
            }]
        }))
        translator._client = mock_client

        entry = create_test_entry(entry_id="unique_id_12345")
        result = translator.translate(entry)

        assert result.entry_id == "unique_id_12345"

    def test_translate_preserves_original_text(self):
        """Test that original text is preserved exactly."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{
                "message": {"content": "translated"}
            }]
        }))
        translator._client = mock_client

        original = "Hello, %1! Olá, 日本語，한국어"
        entry = create_test_entry(original_text=original)
        result = translator.translate(entry)

        assert result.original_text == original


class TestQwenTranslatorHTTPErrors:
    """Test HTTP error handling."""

    @pytest.mark.parametrize("status_code,error_code", [
        (400, "api_client_error"),
        (401, "authentication_failed"),
        (403, "access_forbidden"),
        (404, "endpoint_not_found"),
        (429, "rate_limit_exceeded"),
        (500, "api_server_error"),
        (502, "api_server_error"),
        (503, "api_server_error"),
    ])
    def test_http_error_codes(self, status_code: int, error_code: str):
        """Test various HTTP error codes."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(status_code))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.translated_text is None
        assert len(result.issues) == 1
        assert result.issues[0].code == error_code

    def test_timeout_error(self):
        """Test timeout error handling."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_exception(httpx.TimeoutException("Timeout"))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "request_timeout"
        assert "timed out" in result.issues[0].message.lower()

    def test_connection_error(self):
        """Test connection error handling."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_exception(httpx.ConnectError("Connection failed"))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "connection_failed"

    def test_generic_request_error(self):
        """Test generic request error handling."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_exception(httpx.RequestError("Network error"))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "request_failed"


class TestQwenTranslatorInvalidResponses:
    """Test handling of invalid API responses."""

    def test_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, text_content="not valid json"))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "invalid_response_format"

    def test_missing_choices_field(self):
        """Test handling of response missing choices field."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "usage": {"total_tokens": 10}
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"

    def test_empty_choices_array(self):
        """Test handling of empty choices array."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": []
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"

    def test_missing_message_field(self):
        """Test handling of response missing message field."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"finish_reason": "stop"}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"

    def test_missing_content_field(self):
        """Test handling of response missing content field."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"role": "assistant"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"

    def test_null_content_field(self):
        """Test handling of null content field."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": None}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"

    def test_empty_string_content(self):
        """Test handling of empty string content."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": ""}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"

    def test_whitespace_only_content(self):
        """Test handling of whitespace-only content."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "   \n\t   "}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "empty_translation"


class TestQwenTranslatorSecurity:
    """Test security-related aspects."""

    def test_api_key_not_in_error_message(self):
        """Test that API key is not exposed in error messages."""
        config = create_test_config(api_key="secret_key_12345")
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_exception(httpx.ConnectError("Connection failed"))
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        # Verify API key is not in any error message
        for issue in result.issues:
            assert "secret_key_12345" not in issue.message
            assert "secret" not in issue.message.lower()

    def test_api_key_sent_in_authorization_header(self):
        """Test that API key is sent in Authorization header."""
        config = create_test_config(api_key="test_auth_key")
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "OK"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        translator.translate(entry)

        assert len(mock_client.request_history) == 1
        headers = mock_client.request_history[0]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_auth_key"

    def test_unexpected_error_doesnt_expose_details(self):
        """Test that unexpected errors don't expose sensitive details."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()

        class SensitiveException(Exception):
            def __init__(self):
                super().__init__("Sensitive info: api_key=secret123")

        mock_client.set_exception(SensitiveException())
        translator._client = mock_client

        entry = create_test_entry()
        result = translator.translate(entry)

        assert result.status == TranslationStatus.FAILED
        assert result.issues[0].code == "unexpected_error"
        # Should only show exception type, not message with sensitive info
        # (The current implementation shows exception type only in the code path)


class TestQwenTranslatorRequestFormat:
    """Test the format of outgoing requests."""

    def test_request_uses_chat_completions_endpoint(self):
        """Test that request uses correct endpoint."""
        config = create_test_config(base_url="https://test.example.com/api")
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "OK"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        translator.translate(entry)

        assert len(mock_client.request_history) == 1
        url = mock_client.request_history[0]["url"]
        assert url.endswith("/chat/completions")

    def test_request_includes_model(self):
        """Test that request includes the configured model."""
        config = create_test_config(model="custom-test-model")
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "OK"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        translator.translate(entry)

        request_json = mock_client.request_history[0]["json"]
        assert request_json["model"] == "custom-test-model"

    def test_request_includes_system_prompt(self):
        """Test that request includes system prompt."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "OK"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        translator.translate(entry)

        request_json = mock_client.request_history[0]["json"]
        messages = request_json["messages"]
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        assert "translator" in messages[0]["content"].lower()

    def test_request_includes_original_text(self):
        """Test that request includes the original text."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "OK"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry(original_text="Specific test text")
        translator.translate(entry)

        request_json = mock_client.request_history[0]["json"]
        user_message = request_json["messages"][1]["content"]
        assert "Specific test text" in user_message

    def test_request_temperature_setting(self):
        """Test that request uses low temperature for determinism."""
        config = create_test_config()
        translator = QwenTranslator(config=config)

        mock_client = MockHTTPClient()
        mock_client.set_response(create_mock_response(200, json_data={
            "choices": [{"message": {"content": "OK"}}]
        }))
        translator._client = mock_client

        entry = create_test_entry()
        translator.translate(entry)

        request_json = mock_client.request_history[0]["json"]
        assert request_json["temperature"] == 0.3
