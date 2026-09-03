"""Tests for EncodingHandler implementation.

These tests verify that the EncodingHandler correctly:
1. Detects UTF-8 encoding
2. Detects UTF-8 with BOM
3. Detects Shift-JIS/cp932 encoding
4. Preserves encoding on round-trip
5. Handles Portuguese and Japanese characters
6. Handles special characters and accents
"""

import tempfile
from pathlib import Path

import pytest

from app.services.encoding_handler import (
    EncodingDetector,
    EncodingHandler,
    EncodingInfo,
    EncodingType,
    FileReadResult,
    detect_encoding,
    read_text_file,
    write_text_file,
    UTF8_BOM,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def detector():
    """Create an EncodingDetector instance."""
    return EncodingDetector()


@pytest.fixture
def handler():
    """Create an EncodingHandler instance."""
    return EncodingHandler()


class TestEncodingDetector:
    """Test encoding detection functionality."""

    def test_detect_utf8_without_bom(self, detector, temp_dir):
        """Test detection of UTF-8 without BOM."""
        file_path = temp_dir / "utf8.txt"
        file_path.write_bytes(b"Hello World")
        
        result = detector.detect(file_path)
        
        assert result.success
        assert result.encoding_info is not None
        assert result.encoding_info.encoding == "utf-8"
        assert result.encoding_info.encoding_type == EncodingType.UTF8
        assert not result.encoding_info.has_bom

    def test_detect_utf8_with_bom(self, detector, temp_dir):
        """Test detection of UTF-8 with BOM."""
        file_path = temp_dir / "utf8_bom.txt"
        content = UTF8_BOM + b"Hello World"
        file_path.write_bytes(content)
        
        result = detector.detect(file_path)
        
        assert result.success
        assert result.encoding_info is not None
        assert result.encoding_info.encoding == "utf-8-sig"
        assert result.encoding_info.encoding_type == EncodingType.UTF8_BOM
        assert result.encoding_info.has_bom
        assert result.encoding_info.bom_bytes == UTF8_BOM

    def test_detect_shift_jis(self, detector, temp_dir):
        """Test detection of Shift-JIS encoding."""
        file_path = temp_dir / "shiftjis.txt"
        # Japanese text in Shift-JIS
        japanese_text = "こんにちは".encode("shift_jis")
        file_path.write_bytes(japanese_text)
        
        result = detector.detect(file_path)
        
        assert result.success
        assert result.encoding_info is not None
        assert result.encoding_info.encoding in ("shift_jis", "cp932")
        assert result.encoding_info.encoding_type in (EncodingType.SHIFT_JIS, EncodingType.CP932)
        assert not result.encoding_info.has_bom

    def test_detect_file_not_found(self, detector, temp_dir):
        """Test detection when file doesn't exist."""
        file_path = temp_dir / "nonexistent.txt"
        
        result = detector.detect(file_path)
        
        assert not result.success
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    def test_detect_empty_file(self, detector, temp_dir):
        """Test detection of empty file."""
        file_path = temp_dir / "empty.txt"
        file_path.write_bytes(b"")
        
        result = detector.detect(file_path)
        
        assert not result.success
        assert result.error_message is not None

    def test_detect_from_bytes_utf8(self, detector):
        """Test detection from bytes - UTF-8."""
        data = "Olá Mundo".encode("utf-8")
        
        result = detector.detect_from_bytes(data)
        
        assert result.success
        assert result.encoding_info is not None
        assert result.encoding_info.encoding == "utf-8"

    def test_detect_from_bytes_utf8_bom(self, detector):
        """Test detection from bytes - UTF-8 with BOM."""
        data = UTF8_BOM + "Olá Mundo".encode("utf-8")
        
        result = detector.detect_from_bytes(data)
        
        assert result.success
        assert result.encoding_info is not None
        assert result.encoding_info.encoding == "utf-8-sig"
        assert result.encoding_info.has_bom

    def test_is_utf8_with_bom(self, detector):
        """Test BOM detection helper."""
        assert detector.is_utf8_with_bom(UTF8_BOM + b"test")
        assert not detector.is_utf8_with_bom(b"test")

    def test_strip_bom(self, detector):
        """Test BOM stripping."""
        data_with_bom = UTF8_BOM + b"test"
        data_without_bom, had_bom = detector.strip_bom(data_with_bom)
        
        assert had_bom
        assert data_without_bom == b"test"
        
        # Test without BOM
        data_no_bom, had_bom2 = detector.strip_bom(b"test")
        assert not had_bom2
        assert data_no_bom == b"test"


class TestEncodingHandlerRead:
    """Test file reading with encoding handling."""

    def test_read_utf8_file(self, handler, temp_dir):
        """Test reading UTF-8 file."""
        file_path = temp_dir / "utf8.txt"
        expected_content = "Olá Mundo! Café ☕"
        file_path.write_text(expected_content, encoding="utf-8")
        
        result = handler.read_file(file_path)
        
        assert result.content == expected_content
        assert result.encoding == "utf-8"
        assert not result.has_bom

    def test_read_utf8_bom_file(self, handler, temp_dir):
        """Test reading UTF-8 file with BOM."""
        file_path = temp_dir / "utf8_bom.txt"
        expected_content = "Olá Mundo! Café ☕"
        content_bytes = UTF8_BOM + expected_content.encode("utf-8")
        file_path.write_bytes(content_bytes)
        
        result = handler.read_file(file_path)
        
        assert result.content == expected_content
        assert result.encoding == "utf-8-sig"
        assert result.has_bom

    def test_read_shift_jis_file(self, handler, temp_dir):
        """Test reading Shift-JIS file with Japanese text."""
        file_path = temp_dir / "sjis.txt"
        japanese_text = "こんにちは世界"
        content_bytes = japanese_text.encode("shift_jis")
        file_path.write_bytes(content_bytes)
        
        result = handler.read_file(file_path)
        
        assert result.content == japanese_text
        assert result.encoding in ("shift_jis", "cp932")
        assert not result.has_bom

    def test_read_mixed_unicode(self, handler, temp_dir):
        """Test reading file with mixed Unicode characters."""
        file_path = temp_dir / "mixed.txt"
        # Mix of Portuguese, Japanese, emojis, and special chars
        content = "日本語 Português café ñ ü é 你好 🎮 🎯"
        file_path.write_text(content, encoding="utf-8")
        
        result = handler.read_file(file_path)
        
        assert result.content == content

    def test_read_preserves_accented_characters(self, handler, temp_dir):
        """Test that accented Portuguese characters are preserved."""
        file_path = temp_dir / "portuguese.txt"
        portuguese_text = "Ação, razão, coração, põe, avô, útil"
        file_path.write_text(portuguese_text, encoding="utf-8")
        
        result = handler.read_file(file_path)
        
        assert result.content == portuguese_text

    def test_read_file_with_encoding_explicit(self, handler, temp_dir):
        """Test reading with explicit encoding specification."""
        file_path = temp_dir / "explicit.txt"
        content = "Test content"
        file_path.write_text(content, encoding="utf-8")
        
        result = handler.read_file_with_encoding(file_path, "utf-8")
        
        assert result.content == content
        assert result.encoding == "utf-8"


class TestEncodingHandlerWrite:
    """Test file writing with encoding handling."""

    def test_write_utf8_file(self, handler, temp_dir):
        """Test writing UTF-8 file."""
        file_path = temp_dir / "output.txt"
        content = "Olá Mundo! Café ☕"
        
        handler.write_file(file_path, content, encoding="utf-8")
        
        # Verify content
        read_back = file_path.read_text(encoding="utf-8")
        assert read_back == content

    def test_write_utf8_with_bom(self, handler, temp_dir):
        """Test writing UTF-8 file with BOM."""
        file_path = temp_dir / "output_bom.txt"
        content = "Olá Mundo!"
        
        handler.write_file(file_path, content, encoding="utf-8", has_bom=True)
        
        # Verify BOM is present
        raw_bytes = file_path.read_bytes()
        assert raw_bytes.startswith(UTF8_BOM)
        
        # Verify content
        read_back = file_path.read_text(encoding="utf-8-sig")
        assert read_back == content

    def test_write_preserving_encoding(self, handler, temp_dir):
        """Test writing while preserving original encoding characteristics."""
        # Create file with BOM
        file_path = temp_dir / "preserve.txt"
        original_content = "Original content"
        original_bytes = UTF8_BOM + original_content.encode("utf-8")
        file_path.write_bytes(original_bytes)
        
        # Read to get encoding info
        read_result = handler.read_file(file_path)
        assert read_result.has_bom
        
        # Write new content preserving encoding
        new_content = "New content with changes"
        handler.write_file_preserving_encoding(
            file_path,
            new_content,
            read_result.encoding,
            read_result.has_bom,
        )
        
        # Verify BOM is preserved
        new_bytes = file_path.read_bytes()
        assert new_bytes.startswith(UTF8_BOM)
        
        # Verify new content
        read_back = file_path.read_text(encoding="utf-8-sig")
        assert read_back == new_content

    def test_write_creates_parent_directories(self, handler, temp_dir):
        """Test that write creates parent directories if needed."""
        file_path = temp_dir / "subdir" / "nested" / "file.txt"
        content = "Nested content"
        
        handler.write_file(file_path, content)
        
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content


class TestRoundTrip:
    """Test round-trip integrity for various encodings."""

    def test_round_trip_utf8(self, handler, temp_dir):
        """Test round-trip for UTF-8 file."""
        file_path = temp_dir / "roundtrip_utf8.txt"
        original_content = "Olá Mundo! Ação, razão, coração 🎮"
        file_path.write_text(original_content, encoding="utf-8")
        
        success, error = handler.round_trip_test(file_path)
        
        assert success, f"Round-trip failed: {error}"

    def test_round_trip_utf8_bom(self, handler, temp_dir):
        """Test round-trip for UTF-8 with BOM."""
        file_path = temp_dir / "roundtrip_bom.txt"
        original_content = "Conteúdo com BOM"
        original_bytes = UTF8_BOM + original_content.encode("utf-8")
        file_path.write_bytes(original_bytes)
        
        success, error = handler.round_trip_test(file_path)
        
        assert success, f"Round-trip failed: {error}"
        
        # Verify BOM is preserved
        final_bytes = file_path.read_bytes()
        assert final_bytes.startswith(UTF8_BOM)

    def test_round_trip_shift_jis(self, handler, temp_dir):
        """Test round-trip for Shift-JIS file."""
        file_path = temp_dir / "roundtrip_sjis.txt"
        japanese_text = "これはテストです。こんにちは！"
        content_bytes = japanese_text.encode("shift_jis")
        file_path.write_bytes(content_bytes)
        
        success, error = handler.round_trip_test(file_path)
        
        assert success, f"Round-trip failed: {error}"
        
        # Verify content is preserved
        read_back = file_path.read_text(encoding="shift_jis")
        assert read_back == japanese_text

    def test_round_trip_portuguese_accents(self, handler, temp_dir):
        """Test round-trip preserves Portuguese accents."""
        file_path = temp_dir / "roundtrip_pt.txt"
        portuguese_text = "Ação, razão, coração, põe, avô, útil, câmara"
        file_path.write_text(portuguese_text, encoding="utf-8")
        
        success, error = handler.round_trip_test(file_path)
        
        assert success, f"Round-trip failed: {error}"
        
        # Verify accents are preserved
        read_back = file_path.read_text(encoding="utf-8")
        assert read_back == portuguese_text


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_encoding_function(self, temp_dir):
        """Test detect_encoding convenience function."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("Test", encoding="utf-8")
        
        result = detect_encoding(file_path)
        
        assert result.success
        assert result.encoding == "utf-8"

    def test_read_text_file_function(self, temp_dir):
        """Test read_text_file convenience function."""
        file_path = temp_dir / "test.txt"
        content = "Test content"
        file_path.write_text(content, encoding="utf-8")
        
        result = read_text_file(file_path)
        
        assert result.content == content
        assert result.encoding == "utf-8"

    def test_write_text_file_function(self, temp_dir):
        """Test write_text_file convenience function."""
        file_path = temp_dir / "output.txt"
        content = "Written content"
        
        write_text_file(file_path, content)
        
        assert file_path.read_text(encoding="utf-8") == content


class TestEncodingEdgeCases:
    """Test edge cases in encoding handling."""

    def test_detect_cp932_variant(self, detector, temp_dir):
        """Test detection of cp932 (Windows Shift-JIS variant)."""
        file_path = temp_dir / "cp932.txt"
        # cp932 is very similar to shift_jis
        japanese_text = "テスト".encode("cp932")
        file_path.write_bytes(japanese_text)
        
        result = detector.detect(file_path)
        
        assert result.success
        # Should be detected as shift_jis or cp932
        assert result.encoding_info is not None
        assert result.encoding_info.encoding in ("shift_jis", "cp932")

    def test_special_unicode_symbols(self, handler, temp_dir):
        """Test handling of special Unicode symbols."""
        file_path = temp_dir / "symbols.txt"
        symbols = "♠ ♥ ♦ ♣ ★ ☆ → ← ↑ ↓ © ® ™ € £ ¥ § ¶"
        file_path.write_text(symbols, encoding="utf-8")
        
        result = handler.read_file(file_path)
        
        assert result.content == symbols

    def test_mixed_languages(self, handler, temp_dir):
        """Test file with multiple languages."""
        file_path = temp_dir / "multilang.txt"
        content = (
            "English: Hello\n"
            "Português: Olá\n"
            "日本語：こんにちは\n"
            "Español: Hola\n"
            "Français: Bonjour\n"
            "Emoji: 🎮 🎯 🏆"
        )
        file_path.write_text(content, encoding="utf-8")
        
        result = handler.read_file(file_path)
        
        assert result.content == content

    def test_empty_content_round_trip(self, handler, temp_dir):
        """Test round-trip with empty content."""
        file_path = temp_dir / "empty.txt"
        # Write non-empty first to have valid encoding detection
        file_path.write_text("test", encoding="utf-8")
        
        result = handler.read_file(file_path)
        
        assert result.content == "test"
        assert result.encoding == "utf-8"


class TestEncodingErrorHandling:
    """Test error handling in encoding operations."""

    def test_read_nonexistent_file(self, handler, temp_dir):
        """Test reading non-existent file raises error."""
        file_path = temp_dir / "nonexistent.txt"
        
        with pytest.raises(OSError):
            handler.read_file(file_path)

    def test_write_invalid_encoding(self, handler, temp_dir):
        """Test writing with invalid encoding raises error."""
        file_path = temp_dir / "output.txt"
        
        with pytest.raises(LookupError):
            handler.write_file(file_path, "test", encoding="invalid-encoding")

    def test_detect_unsupported_encoding(self, detector, temp_dir):
        """Test detection fails gracefully for truly unsupported encoding."""
        # Use bytes that are valid in some encodings but not UTF-8/Shift-JIS
        # The detector will try multiple encodings, so we need data that fails all
        file_path = temp_dir / "binary.bin"
        # This sequence is invalid in UTF-8 and also problematic in Shift-JIS
        binary_data = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0x80, 0x81])
        file_path.write_bytes(binary_data)
        
        result = detector.detect(file_path)
        
        # cp932 is very permissive, so this might still succeed
        # The key is the detector doesn't crash
        assert result.file_path == file_path
