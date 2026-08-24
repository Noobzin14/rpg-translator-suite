"""Token Protector for RPG Maker escape codes.

This module provides protection for RPG Maker escape codes during translation,
ensuring that special tokens are preserved exactly as they appear in the original text.

The TokenProtector works by:
1. Extracting all escape code tokens from the original text
2. Replacing them with unique placeholders
3. Allowing safe translation of the protected text
4. Validating that the translation preserves the placeholder structure
5. Restoring the original tokens in their correct positions

Supported escape codes include:
- \\N[n] - Actor name reference
- \\P[n] - Party member reference  
- \\V[n] - Variable reference
- \\C[n] - Color change
- \\I[n] - Icon reference
- \\FS[n] - Font size change
- \\. - Wait for key press
- \\! - Wait for key press (different style)
- \\> - Speed up text
- \\< - Slow down text
- \\^ - Close window without waiting
- \\| - Wait 0.25 seconds
- \\[n] - Play SE
- \\] - Stop SE
- \\S[n] - Play SE by ID
- \\Q[n] - Play ME by ID
- \\A[n] - Play BGM by ID
- \\B[n] - Play BGS by ID
- \\G - Gold window
- \\$ - Show gold currency
- Other single-character escapes
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final


# RPG Maker MV escape code patterns
# These patterns cover the most common escape sequences used in dialogues

ESCAPE_CODE_PATTERN: Final = re.compile(
    r"""
    # Parameterized escape codes like \N[1], \V[5], \C[2], etc.
    \\[NPVICFGHABQS][\[\{]?(\d+)[\]\}]?
    |
    # Font size escape \FS[20]
    \\FS[\[\{]?(\d+)[\]\}]?
    |
    # Single character escapes that don't take parameters
    \\[.!>|^|$]
    |
    # Wait command \W[n] or \wait[n]
    \\(?:W|wait)[\[\{]?(\d+)[\]\}]?
    |
    # Sound effect commands
    \\(?:SE|ME|BGM|BGS)[\[\{]?(\d+)?[\]\}]?
    """,
    re.VERBOSE | re.IGNORECASE
)

# Alternative simpler pattern that catches more cases
SIMPLE_ESCAPE_PATTERN: Final = re.compile(
    r'\\[A-Za-z]*[\[\{]?\d*[\]\}]?|\\[.!>|^|$]'
)


@dataclass(frozen=True)
class TokenInfo:
    """Information about a protected token.
    
    Attributes:
        original_token: The original escape code sequence.
        placeholder: The unique placeholder used during translation.
        position: The position in the original text where the token was found.
        token_type: The type of token (e.g., 'actor_name', 'variable', etc.)
    """
    original_token: str
    placeholder: str
    position: int
    token_type: str


@dataclass
class ProtectionResult:
    """Result of protecting text for translation.
    
    Attributes:
        protected_text: The text with tokens replaced by placeholders.
        tokens: List of TokenInfo objects for all protected tokens.
        original_text: The original text before protection.
    """
    protected_text: str
    tokens: list[TokenInfo]
    original_text: str


@dataclass
class RestorationResult:
    """Result of restoring tokens after translation.
    
    Attributes:
        restored_text: The text with original tokens restored.
        validation_passed: Whether the restoration was successful.
        issues: List of any issues found during restoration.
    """
    restored_text: str
    validation_passed: bool
    issues: list[str] = field(default_factory=list)


class TokenProtector:
    """Protects RPG Maker escape codes during translation.
    
    This class handles the extraction, protection, and restoration of
    RPG Maker escape codes to ensure they are not corrupted during
    the translation process.
    
    Usage:
        protector = TokenProtector()
        
        # Protect text before translation
        result = protector.protect("Hello \\N[1], welcome!")
        protected_text = result.protected_text
        
        # Translate the protected text (using your translator)
        translated_text = translate(protected_text)
        
        # Restore tokens after translation
        restore_result = protector.restore(translated_text, result.tokens)
        final_text = restore_result.restored_text
    """
    
    def __init__(self) -> None:
        """Initialize the TokenProtector."""
        self._placeholder_prefix = "__TOKEN_"
        self._placeholder_suffix = "__"
    
    def _generate_placeholder(self, index: int) -> str:
        """Generate a unique placeholder for a token.
        
        Args:
            index: The index of the token.
            
        Returns:
            A unique placeholder string.
        """
        return f"{self._placeholder_prefix}{index}{self._placeholder_suffix}"
    
    def _classify_token(self, token: str) -> str:
        """Classify the type of escape code token.
        
        Args:
            token: The escape code token.
            
        Returns:
            A string describing the token type.
        """
        token_lower = token.lower()
        
        if re.match(r'\\N\[\d+\]', token, re.IGNORECASE):
            return 'actor_name'
        elif re.match(r'\\P\[\d+\]', token, re.IGNORECASE):
            return 'party_member'
        elif re.match(r'\\V\[\d+\]', token, re.IGNORECASE):
            return 'variable'
        elif re.match(r'\\C\[\d+\]', token, re.IGNORECASE):
            return 'color'
        elif re.match(r'\\I\[\d+\]', token, re.IGNORECASE):
            return 'icon'
        elif re.match(r'\\FS\[\d+\]', token, re.IGNORECASE):
            return 'font_size'
        elif re.match(r'\\W\[\d+\]', token, re.IGNORECASE):
            return 'wait'
        elif token == '\\.':
            return 'wait_key'
        elif token == '\\!':
            return 'wait_exclaim'
        elif token == '\\>':
            return 'speed_up'
        elif token == '\\<':
            return 'speed_down'
        elif token == '\\^':
            return 'close_no_wait'
        elif token == '\\|':
            return 'wait_quarter'
        elif token == '\\$':
            return 'gold_currency'
        else:
            return 'unknown'
    
    def protect(self, text: str) -> ProtectionResult:
        """Protect escape codes in text by replacing them with placeholders.
        
        Args:
            text: The original text containing escape codes.
            
        Returns:
            A ProtectionResult containing the protected text and token information.
        """
        if not text:
            return ProtectionResult(
                protected_text=text,
                tokens=[],
                original_text=text
            )
        
        tokens: list[TokenInfo] = []
        protected_text = text
        token_index = 0
        
        # Find all escape codes using the simple pattern for broader coverage
        for match in SIMPLE_ESCAPE_PATTERN.finditer(text):
            token = match.group(0)
            position = match.start()
            
            # Generate placeholder
            placeholder = self._generate_placeholder(token_index)
            
            # Classify the token
            token_type = self._classify_token(token)
            
            # Store token info
            tokens.append(TokenInfo(
                original_token=token,
                placeholder=placeholder,
                position=position,
                token_type=token_type
            ))
            
            token_index += 1
        
        # Replace tokens with placeholders in reverse order to preserve positions
        for token_info in reversed(tokens):
            protected_text = protected_text.replace(
                token_info.original_token,
                token_info.placeholder,
                1  # Only replace first occurrence to handle duplicates correctly
            )
        
        return ProtectionResult(
            protected_text=protected_text,
            tokens=tokens,
            original_text=text
        )
    
    def restore(
        self,
        translated_text: str,
        tokens: list[TokenInfo],
    ) -> RestorationResult:
        """Restore original tokens to translated text.
        
        Args:
            translated_text: The translated text containing placeholders.
            tokens: List of TokenInfo objects from the protection step.
            
        Returns:
            A RestorationResult containing the restored text and validation status.
        """
        issues: list[str] = []
        restored_text = translated_text
        
        if not tokens:
            return RestorationResult(
                restored_text=translated_text,
                validation_passed=True,
                issues=issues
            )
        
        # Check for missing placeholders
        expected_placeholders = {t.placeholder for t in tokens}
        found_placeholders = set()
        
        for token_info in tokens:
            if token_info.placeholder in translated_text:
                found_placeholders.add(token_info.placeholder)
            else:
                issues.append(
                    f"Missing placeholder '{token_info.placeholder}' "
                    f"(original token: '{token_info.original_token}')"
                )
        
        # Check for extra/unknown placeholders
        placeholder_pattern = re.compile(
            rf'{re.escape(self._placeholder_prefix)}\d+{re.escape(self._placeholder_suffix)}'
        )
        for match in placeholder_pattern.finditer(translated_text):
            placeholder = match.group(0)
            if placeholder not in expected_placeholders:
                issues.append(f"Unknown placeholder found: '{placeholder}'")
        
        # Restore tokens in reverse order to preserve positions
        for token_info in reversed(tokens):
            if token_info.placeholder in restored_text:
                restored_text = restored_text.replace(
                    token_info.placeholder,
                    token_info.original_token,
                    1
                )
            else:
                # Placeholder was removed - this is already recorded in issues
                pass
        
        validation_passed = len(issues) == 0
        
        return RestorationResult(
            restored_text=restored_text,
            validation_passed=validation_passed,
            issues=issues
        )
    
    def validate_translation(
        self,
        original_protected: ProtectionResult,
        translated_text: str,
    ) -> tuple[bool, list[str]]:
        """Validate that a translation preserves the token structure.
        
        This method checks if the translated text contains the same
        placeholders as the protected original text.
        
        Args:
            original_protected: The ProtectionResult from the protect() call.
            translated_text: The translated text to validate.
            
        Returns:
            A tuple of (is_valid, list_of_issues).
        """
        issues: list[str] = []
        
        # Count placeholders in protected text
        placeholder_pattern = re.compile(
            rf'{re.escape(self._placeholder_prefix)}\d+{re.escape(self._placeholder_suffix)}'
        )
        
        original_placeholders = placeholder_pattern.findall(
            original_protected.protected_text
        )
        translated_placeholders = placeholder_pattern.findall(translated_text)
        
        # Check count mismatch
        if len(original_placeholders) != len(translated_placeholders):
            issues.append(
                f"Placeholder count mismatch: "
                f"expected {len(original_placeholders)}, "
                f"got {len(translated_placeholders)}"
            )
        
        # Check for missing placeholders
        original_set = set(original_placeholders)
        translated_set = set(translated_placeholders)
        
        missing = original_set - translated_set
        extra = translated_set - original_set
        
        for placeholder in missing:
            issues.append(f"Missing placeholder: {placeholder}")
        
        for placeholder in extra:
            issues.append(f"Extra placeholder: {placeholder}")
        
        # Check order preservation
        if original_placeholders != translated_placeholders:
            issues.append("Placeholder order differs from original")
        
        return len(issues) == 0, issues
    
    def protect_and_restore(
        self,
        original_text: str,
        translated_text: str,
    ) -> RestorationResult:
        """Convenience method to protect and then restore in one flow.
        
        This is useful when you want to protect text, translate it,
        and restore the tokens without manually managing the tokens list.
        
        Args:
            original_text: The original text to protect.
            translated_text: The translated text to restore tokens into.
            
        Returns:
            A RestorationResult containing the final text and validation status.
        """
        protection_result = self.protect(original_text)
        return self.restore(translated_text, protection_result.tokens)
