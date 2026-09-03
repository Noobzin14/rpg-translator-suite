"""Encoding detection and handling for RPG Maker MV files.

This module provides a centralized abstraction for reading and writing
text files with proper encoding detection and preservation.

Supported encodings:
- UTF-8 (with and without BOM)
- Shift-JIS (cp932)

The encoding handler ensures round-trip preservation of:
- Original encoding
- BOM when present
- Content integrity
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EncodingType(Enum):
    """Known encoding types."""
    UTF8 = "utf-8"
    UTF8_BOM = "utf-8-sig"
    SHIFT_JIS = "shift_jis"
    CP932 = "cp932"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EncodingInfo:
    """Information about detected encoding.
    
    Attributes:
        encoding: The detected encoding name.
        encoding_type: The categorized encoding type.
        has_bom: Whether the file has a BOM.
        confidence: Confidence level of detection (0.0 to 1.0).
        bom_bytes: The BOM bytes if present.
    """
    encoding: str
    encoding_type: EncodingType
    has_bom: bool = False
    confidence: float = 1.0
    bom_bytes: bytes = field(default_factory=bytes)


@dataclass
class EncodingDetectionResult:
    """Result of encoding detection.
    
    Attributes:
        success: Whether detection was successful.
        encoding_info: Detected encoding information (if successful).
        error_message: Error message (if detection failed).
        file_path: Path to the analyzed file.
    """
    success: bool
    encoding_info: EncodingInfo | None = None
    error_message: str | None = None
    file_path: Path | None = None
    
    @property
    def encoding(self) -> str | None:
        """Get the detected encoding name."""
        return self.encoding_info.encoding if self.encoding_info else None


# BOM signatures for common encodings
BOM_SIGNATURES: dict[bytes, tuple[str, EncodingType]] = {
    codecs.BOM_UTF8: ("utf-8-sig", EncodingType.UTF8_BOM),
    codecs.BOM_UTF16_LE: ("utf-16-le", EncodingType.UNKNOWN),
    codecs.BOM_UTF16_BE: ("utf-16-be", EncodingType.UNKNOWN),
}

# UTF-8 BOM
UTF8_BOM = codecs.BOM_UTF8


class EncodingDetector:
    """Detects text file encodings.
    
    This detector uses a conservative approach:
    1. Check for BOM first (definitive)
    2. Try UTF-8 decoding
    3. Try Shift-JIS decoding
    4. Return error if unable to determine safely
    
    It does NOT try indiscriminate sequences of encodings.
    """
    
    def __init__(self) -> None:
        """Initialize the EncodingDetector."""
        self._supported_encodings = ["utf-8", "utf-8-sig", "shift_jis", "cp932"]
    
    def detect(self, file_path: Path) -> EncodingDetectionResult:
        """Detect the encoding of a file.
        
        Args:
            file_path: Path to the file to analyze.
            
        Returns:
            EncodingDetectionResult with detection outcome.
        """
        if not file_path.exists():
            return EncodingDetectionResult(
                success=False,
                error_message=f"File not found: {file_path}",
                file_path=file_path,
            )
        
        try:
            raw_bytes = file_path.read_bytes()
        except OSError as e:
            return EncodingDetectionResult(
                success=False,
                error_message=f"Cannot read file: {e}",
                file_path=file_path,
            )
        
        return self.detect_from_bytes(raw_bytes, file_path)
    
    def detect_from_bytes(self, data: bytes, file_path: Path | None = None) -> EncodingDetectionResult:
        """Detect encoding from raw bytes.
        
        Args:
            data: Raw bytes to analyze.
            file_path: Optional path for error reporting.
            
        Returns:
            EncodingDetectionResult with detection outcome.
        """
        if not data:
            return EncodingDetectionResult(
                success=False,
                error_message="Empty file cannot be analyzed for encoding",
                file_path=file_path,
            )
        
        # Step 1: Check for BOM
        for bom_bytes, (encoding_name, encoding_type) in BOM_SIGNATURES.items():
            if data.startswith(bom_bytes):
                return EncodingDetectionResult(
                    success=True,
                    encoding_info=EncodingInfo(
                        encoding=encoding_name,
                        encoding_type=encoding_type,
                        has_bom=True,
                        confidence=1.0,
                        bom_bytes=bom_bytes,
                    ),
                    file_path=file_path,
                )
        
        # Step 2: Try UTF-8 (most common for modern projects)
        try:
            data.decode("utf-8")
            return EncodingDetectionResult(
                success=True,
                encoding_info=EncodingInfo(
                    encoding="utf-8",
                    encoding_type=EncodingType.UTF8,
                    has_bom=False,
                    confidence=0.95,
                ),
                file_path=file_path,
            )
        except UnicodeDecodeError:
            pass
        
        # Step 3: Try Shift-JIS (common for Japanese RPG Maker games)
        try:
            data.decode("shift_jis")
            return EncodingDetectionResult(
                success=True,
                encoding_info=EncodingInfo(
                    encoding="shift_jis",
                    encoding_type=EncodingType.SHIFT_JIS,
                    has_bom=False,
                    confidence=0.9,
                ),
                file_path=file_path,
            )
        except UnicodeDecodeError:
            pass
        
        # Step 4: Try cp932 (Windows variant of Shift-JIS)
        try:
            data.decode("cp932")
            return EncodingDetectionResult(
                success=True,
                encoding_info=EncodingInfo(
                    encoding="cp932",
                    encoding_type=EncodingType.CP932,
                    has_bom=False,
                    confidence=0.85,
                ),
                file_path=file_path,
            )
        except UnicodeDecodeError:
            pass
        
        # Unable to determine encoding
        return EncodingDetectionResult(
            success=False,
            error_message="Unable to determine encoding - file may be binary or use unsupported encoding",
            file_path=file_path,
        )
    
    def is_utf8_with_bom(self, data: bytes) -> bool:
        """Check if bytes start with UTF-8 BOM.
        
        Args:
            data: Raw bytes to check.
            
        Returns:
            True if UTF-8 BOM is present.
        """
        return data.startswith(UTF8_BOM)
    
    def strip_bom(self, data: bytes) -> tuple[bytes, bool]:
        """Strip BOM from bytes if present.
        
        Args:
            data: Raw bytes that may contain BOM.
            
        Returns:
            Tuple of (data_without_bom, had_bom).
        """
        for bom_bytes in BOM_SIGNATURES.keys():
            if data.startswith(bom_bytes):
                return data[len(bom_bytes):], True
        return data, False


@dataclass
class FileReadResult:
    """Result of reading a file with encoding handling.
    
    Attributes:
        content: The text content.
        encoding: The encoding used to read the file.
        has_bom: Whether the file had a BOM.
        original_bytes: The original raw bytes (for reference).
    """
    content: str
    encoding: str
    has_bom: bool
    original_bytes: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EncodingHandler:
    """Handles reading and writing files with proper encoding support.
    
    This handler ensures:
    - Proper encoding detection
    - BOM preservation on write
    - Round-trip integrity
    - No silent encoding assumptions
    
    Usage:
        handler = EncodingHandler()
        
        # Read with automatic encoding detection
        result = handler.read_file(file_path)
        content = result.content
        encoding = result.encoding
        
        # Write preserving original encoding
        handler.write_file(file_path, content, encoding=result.encoding, 
                          has_bom=result.has_bom)
    """
    
    def __init__(self, detector: EncodingDetector | None = None) -> None:
        """Initialize the EncodingHandler.
        
        Args:
            detector: Optional custom EncodingDetector instance.
        """
        self._detector = detector or EncodingDetector()
    
    def read_file(self, file_path: Path) -> FileReadResult:
        """Read a file with automatic encoding detection.
        
        Args:
            file_path: Path to the file to read.
            
        Returns:
            FileReadResult with content and encoding information.
            
        Raises:
            ValueError: If encoding detection fails.
            OSError: If file cannot be read.
        """
        # Read raw bytes first
        try:
            raw_bytes = file_path.read_bytes()
        except OSError as e:
            raise OSError(f"Cannot read file: {e}") from e
        
        # Detect encoding
        detection_result = self._detector.detect_from_bytes(raw_bytes, file_path)
        
        if not detection_result.success:
            raise ValueError(detection_result.error_message)
        
        encoding_info = detection_result.encoding_info
        assert encoding_info is not None  # Type guard
        encoding = encoding_info.encoding
        
        # Strip BOM if present for clean decoding
        clean_bytes, had_bom = self._detector.strip_bom(raw_bytes)
        
        # Decode with detected encoding
        try:
            # Use the base encoding (without -sig suffix) for actual decoding
            decode_encoding = encoding.replace("-sig", "")
            content = clean_bytes.decode(decode_encoding)
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode file with {encoding}: {e}") from e
        
        return FileReadResult(
            content=content,
            encoding=encoding,
            has_bom=had_bom,
            original_bytes=raw_bytes,
            metadata={
                "detected_type": encoding_info.encoding_type.value,
                "confidence": encoding_info.confidence,
            },
        )
    
    def read_file_with_encoding(self, file_path: Path, encoding: str) -> FileReadResult:
        """Read a file with specified encoding.
        
        Args:
            file_path: Path to the file to read.
            encoding: Explicit encoding to use.
            
        Returns:
            FileReadResult with content and encoding information.
            
        Raises:
            ValueError: If decoding fails.
            OSError: If file cannot be read.
        """
        try:
            raw_bytes = file_path.read_bytes()
        except OSError as e:
            raise OSError(f"Cannot read file: {e}") from e
        
        # Check for BOM
        clean_bytes, had_bom = self._detector.strip_bom(raw_bytes)
        
        # Decode with specified encoding
        decode_encoding = encoding.replace("-sig", "")
        try:
            content = clean_bytes.decode(decode_encoding)
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode file with {encoding}: {e}") from e
        
        return FileReadResult(
            content=content,
            encoding=encoding,
            has_bom=had_bom,
            original_bytes=raw_bytes,
        )
    
    def write_file(
        self,
        file_path: Path,
        content: str,
        encoding: str = "utf-8",
        has_bom: bool = False,
    ) -> None:
        """Write content to a file with specified encoding.
        
        Args:
            file_path: Path to the file to write.
            content: Text content to write.
            encoding: Encoding to use (default: utf-8).
            has_bom: Whether to prepend BOM (default: False).
            
        Raises:
            ValueError: If encoding is invalid.
            OSError: If file cannot be written.
        """
        # Determine the actual encoding for encoding
        write_encoding = encoding.replace("-sig", "")
        
        # Encode content
        try:
            encoded_bytes = content.encode(write_encoding)
        except UnicodeEncodeError as e:
            raise ValueError(f"Failed to encode content with {write_encoding}: {e}") from e
        
        # Prepend BOM if required
        if has_bom:
            if encoding == "utf-8-sig" or encoding == "utf-8":
                encoded_bytes = UTF8_BOM + encoded_bytes
        
        # Write to file
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(encoded_bytes)
        except OSError as e:
            raise OSError(f"Cannot write file: {e}") from e
    
    def write_file_preserving_encoding(
        self,
        file_path: Path,
        content: str,
        original_encoding: str,
        original_has_bom: bool,
    ) -> None:
        """Write content preserving the original file's encoding characteristics.
        
        This is the recommended method for round-trip file operations.
        
        Args:
            file_path: Path to the file to write.
            content: Text content to write.
            original_encoding: The original file's encoding.
            original_has_bom: Whether the original file had a BOM.
            
        Raises:
            ValueError: If encoding is invalid.
            OSError: If file cannot be written.
        """
        self.write_file(
            file_path=file_path,
            content=content,
            encoding=original_encoding,
            has_bom=original_has_bom,
        )
    
    def round_trip_test(self, file_path: Path) -> tuple[bool, str]:
        """Test round-trip integrity for a file.
        
        Reads and writes the file (to memory), verifying that
        the content can be preserved exactly.
        
        Args:
            file_path: Path to the file to test.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Read
            read_result = self.read_file(file_path)
            
            # Write to temporary location
            temp_path = file_path.with_suffix(file_path.suffix + ".roundtrip_test")
            self.write_file_preserving_encoding(
                temp_path,
                read_result.content,
                read_result.encoding,
                read_result.has_bom,
            )
            
            # Read back
            re_read_result = self.read_file(temp_path)
            
            # Compare
            if read_result.content != re_read_result.content:
                return False, "Content mismatch after round-trip"
            
            if read_result.has_bom != re_read_result.has_bom:
                return False, "BOM status mismatch after round-trip"
            
            # Clean up
            temp_path.unlink(missing_ok=True)
            
            return True, ""
            
        except Exception as e:
            return False, str(e)


# Convenience functions for simple use cases
def detect_encoding(file_path: Path) -> EncodingDetectionResult:
    """Detect encoding of a file.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        EncodingDetectionResult with detection outcome.
    """
    detector = EncodingDetector()
    return detector.detect(file_path)


def read_text_file(file_path: Path) -> FileReadResult:
    """Read a text file with automatic encoding detection.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        FileReadResult with content and encoding info.
        
    Raises:
        ValueError: If encoding detection fails.
    """
    handler = EncodingHandler()
    return handler.read_file(file_path)


def write_text_file(
    file_path: Path,
    content: str,
    encoding: str = "utf-8",
    has_bom: bool = False,
) -> None:
    """Write a text file with specified encoding.
    
    Args:
        file_path: Path to the file.
        content: Text content to write.
        encoding: Encoding to use.
        has_bom: Whether to write BOM.
        
    Raises:
        ValueError: If encoding is invalid.
    """
    handler = EncodingHandler()
    handler.write_file(file_path, content, encoding, has_bom)
