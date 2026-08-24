"""Tests for TokenProtector implementation.

These tests verify that the TokenProtector correctly:
1. Identifies and protects RPG Maker escape codes
2. Preserves token order, quantity, and position
3. Detects missing, extra, or altered placeholders
4. Restores tokens exactly as they appeared in the original
5. Handles edge cases like Unicode, empty strings, repeated tokens
"""

import pytest

from app.utils.token_protector import (
    ProtectionResult,
    RestorationResult,
    TokenInfo,
    TokenProtector,
)


@pytest.fixture
def protector():
    """Create a TokenProtector instance."""
    return TokenProtector()


class TestTokenProtectorBasic:
    """Test basic TokenProtector functionality."""

    def test_no_tokens(self, protector):
        """Test text without any tokens."""
        text = "Hello, world!"
        result = protector.protect(text)
        
        assert result.protected_text == text
        assert len(result.tokens) == 0
        assert result.original_text == text

    def test_single_token(self, protector):
        """Test text with a single token."""
        text = "Hello \\N[1]!"
        result = protector.protect(text)
        
        assert len(result.tokens) == 1
        assert result.tokens[0].original_token == "\\N[1]"
        assert "__TOKEN_0__" in result.protected_text
        assert "\\N[1]" not in result.protected_text

    def test_multiple_tokens(self, protector):
        """Test text with multiple different tokens."""
        text = "\\N[1] has \\V[5] gold."
        result = protector.protect(text)
        
        assert len(result.tokens) == 2
        assert result.tokens[0].original_token == "\\N[1]"
        assert result.tokens[1].original_token == "\\V[5]"

    def test_repeated_tokens(self, protector):
        """Test text with repeated tokens."""
        text = "\\N[1] met \\N[1] again."
        result = protector.protect(text)
        
        # Each occurrence should be tracked separately
        assert len(result.tokens) == 2
        assert result.tokens[0].original_token == "\\N[1]"
        assert result.tokens[1].original_token == "\\N[1]"

    def test_adjacent_tokens(self, protector):
        """Test tokens that are adjacent to each other."""
        text = "Hello\\N[1]\\V[2]!"
        result = protector.protect(text)
        
        assert len(result.tokens) == 2
        assert result.tokens[0].original_token == "\\N[1]"
        assert result.tokens[1].original_token == "\\V[2]"

    def test_tokens_at_start(self, protector):
        """Test tokens at the beginning of text."""
        text = "\\N[1] is the hero."
        result = protector.protect(text)
        
        assert len(result.tokens) == 1
        assert result.tokens[0].position == 0

    def test_tokens_at_end(self, protector):
        """Test tokens at the end of text."""
        text = "The hero is \\N[1]."
        result = protector.protect(text)
        
        assert len(result.tokens) == 1
        # Position should be near the end
        assert result.tokens[0].position > 0

    def test_multiple_token_types(self, protector):
        """Test various token types."""
        text = "\\N[1]\\P[2]\\V[3]\\C[4]\\I[5]\\FS[20]"
        result = protector.protect(text)
        
        assert len(result.tokens) == 6
        token_types = [t.token_type for t in result.tokens]
        assert 'actor_name' in token_types
        assert 'party_member' in token_types
        assert 'variable' in token_types
        assert 'color' in token_types
        assert 'icon' in token_types
        assert 'font_size' in token_types

    def test_unicode_with_tokens(self, protector):
        """Test tokens mixed with Unicode text."""
        text = "こんにちは\\N[1]さん！"
        result = protector.protect(text)
        
        assert len(result.tokens) == 1
        assert result.tokens[0].original_token == "\\N[1]"
        
        # Restore should work with Unicode
        restore_result = protector.restore(result.protected_text, result.tokens)
        assert restore_result.restored_text == text


class TestTokenProtectorRestoration:
    """Test token restoration functionality."""

    def test_round_trip_complete(self, protector):
        """Test complete round-trip: protect -> translate -> restore."""
        original = "Hello \\N[1], you have \\V[5] gold!"
        
        # Protect
        protect_result = protector.protect(original)
        
        # Simulate translation (just modify the non-token parts)
        translated = protect_result.protected_text.replace("Hello", "Olá")
        translated = translated.replace("you have", "você tem")
        translated = translated.replace("gold", "ouro")
        
        # Restore
        restore_result = protector.restore(translated, protect_result.tokens)
        
        assert restore_result.validation_passed
        assert len(restore_result.issues) == 0
        
        # Verify tokens are restored exactly
        assert "\\N[1]" in restore_result.restored_text
        assert "\\V[5]" in restore_result.restored_text

    def test_placeholder_removed(self, protector):
        """Test detection of removed placeholder."""
        original = "Hello \\N[1]!"
        protect_result = protector.protect(original)
        
        # Simulate translation that removes placeholder
        translated = "Hello world!"  # Placeholder removed
        
        restore_result = protector.restore(translated, protect_result.tokens)
        
        assert not restore_result.validation_passed
        assert len(restore_result.issues) > 0
        assert any("Missing" in issue for issue in restore_result.issues)

    def test_placeholder_duplicated(self, protector):
        """Test detection of duplicated placeholder."""
        original = "Hello \\N[1]!"
        protect_result = protector.protect(original)
        
        # Simulate translation that duplicates placeholder
        translated = protect_result.protected_text + " " + protect_result.protected_text
        
        restore_result = protector.restore(translated, protect_result.tokens)
        
        # Should still restore but may have issues
        # The validation should detect the extra placeholder
        is_valid, issues = protector.validate_translation(protect_result, translated)
        assert not is_valid

    def test_placeholder_altered(self, protector):
        """Test detection of altered placeholder."""
        original = "Hello \\N[1]!"
        protect_result = protector.protect(original)
        
        # Simulate translation that alters placeholder
        translated = protect_result.protected_text.replace("__TOKEN_0__", "__TOKEN_999__")
        
        is_valid, issues = protector.validate_translation(protect_result, translated)
        
        assert not is_valid
        assert any("Missing" in issue for issue in issues)


class TestTokenProtectorValidation:
    """Test validation functionality."""

    def test_validate_preserved_placeholders(self, protector):
        """Test validation when placeholders are preserved."""
        original = "Text \\N[1] and \\V[2]"
        protect_result = protector.protect(original)
        
        # Translation preserves placeholders exactly
        translated = "Texto __TOKEN_0__ e __TOKEN_1__"
        
        is_valid, issues = protector.validate_translation(protect_result, translated)
        
        assert is_valid
        assert len(issues) == 0

    def test_validate_count_mismatch(self, protector):
        """Test validation detects count mismatch."""
        original = "Text \\N[1] and \\V[2]"
        protect_result = protector.protect(original)
        
        # Translation has different number of placeholders
        translated = "Texto __TOKEN_0__"
        
        is_valid, issues = protector.validate_translation(protect_result, translated)
        
        assert not is_valid
        assert any("count" in issue.lower() for issue in issues)

    def test_validate_order_difference(self, protector):
        """Test validation detects order difference."""
        original = "\\N[1] and \\V[2]"
        protect_result = protector.protect(original)
        
        # Translation has reversed order
        translated = "__TOKEN_1__ and __TOKEN_0__"
        
        is_valid, issues = protector.validate_translation(protect_result, translated)
        
        assert not is_valid
        assert any("order" in issue.lower() for issue in issues)


class TestTokenProtectorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string(self, protector):
        """Test empty string handling."""
        result = protector.protect("")
        
        assert result.protected_text == ""
        assert len(result.tokens) == 0
        
        restore_result = protector.restore("", result.tokens)
        assert restore_result.restored_text == ""
        assert restore_result.validation_passed

    def test_only_tokens(self, protector):
        """Test text containing only tokens."""
        text = "\\N[1]\\V[2]\\C[3]"
        result = protector.protect(text)
        
        assert len(result.tokens) == 3
        
        # Restore should give back exact original
        restore_result = protector.restore(result.protected_text, result.tokens)
        assert restore_result.restored_text == text

    def test_single_character_escapes(self, protector):
        """Test single character escape codes."""
        text = "Wait\\.exclaim\\!speed\\>slow\\<"
        result = protector.protect(text)
        
        assert len(result.tokens) >= 4  # At least these four escapes

    def test_convenience_method(self, protector):
        """Test the protect_and_restore convenience method."""
        original = "Hello \\N[1]!"
        translated = "Olá __TOKEN_0__!"
        
        result = protector.protect_and_restore(original, translated)
        
        assert result.validation_passed
        assert "\\N[1]" in result.restored_text


class TestTokenProtectorIntegration:
    """Integration tests simulating real usage."""

    def test_full_workflow(self, protector):
        """Test complete workflow from protection to restoration."""
        # Original RPG Maker dialogue
        original = "\\N[1]: Welcome to \\C[2]the castle\\C[0]!\\.|Please choose your path."
        
        # Step 1: Protect
        protect_result = protector.protect(original)
        assert len(protect_result.tokens) > 0
        
        # Step 2: Simulate translation
        # In real scenario, this would call an API
        translated = protect_result.protected_text
        translated = translated.replace("Welcome to", "Bem-vindo ao")
        translated = translated.replace("castle", "castelo")
        translated = translated.replace("Please choose your path", "Por favor escolha seu caminho")
        
        # Step 3: Validate
        is_valid, issues = protector.validate_translation(protect_result, translated)
        assert is_valid, f"Validation failed: {issues}"
        
        # Step 4: Restore
        restore_result = protector.restore(translated, protect_result.tokens)
        
        assert restore_result.validation_passed
        assert "\\N[1]" in restore_result.restored_text
        assert "\\C[2]" in restore_result.restored_text
        assert "\\C[0]" in restore_result.restored_text
        assert "\\." in restore_result.restored_text
        assert "\\|" in restore_result.restored_text
