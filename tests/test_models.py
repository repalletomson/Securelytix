"""
Tests for core data models.
"""
import pytest
from src.models import PIIMatch, PIIResult, ErrorResult


def test_pii_match_creation():
    """Test PIIMatch data model creation."""
    match = PIIMatch(
        text="John Doe",
        pii_type="name",
        confidence=0.95,
        start_pos=0,
        end_pos=8
    )
    assert match.text == "John Doe"
    assert match.pii_type == "name"
    assert match.confidence == 0.95


def test_pii_result_creation():
    """Test PIIResult data model creation."""
    match = PIIMatch("John Doe", "name", 0.95, 0, 8)
    result = PIIResult(
        original_text="Patient: John Doe",
        pii_matches=[match],
        processing_metadata={"ocr_engine": "tesseract"}
    )
    assert result.original_text == "Patient: John Doe"
    assert len(result.pii_matches) == 1
    assert result.redacted_image_path is None


def test_error_result_creation():
    """Test ErrorResult data model creation."""
    error = ErrorResult(
        error_type="InvalidFormat",
        error_message="File is not a valid JPEG",
        stage="input",
        diagnostic_info={"file_type": "PNG"}
    )
    assert error.error_type == "InvalidFormat"
    assert error.stage == "input"