"""
Core data models for the OCR PII Pipeline.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class PIIMatch:
    """Represents a detected PII element in text."""
    text: str
    pii_type: str  # 'name', 'address', 'phone', 'medical_id', 'ssn'
    confidence: float
    start_pos: int
    end_pos: int


@dataclass
class PIIResult:
    """Complete result from OCR PII pipeline processing."""
    original_text: str
    pii_matches: List[PIIMatch]
    processing_metadata: Dict[str, Any]
    redacted_image_path: Optional[str] = None


@dataclass
class ErrorResult:
    """Error information when pipeline processing fails."""
    error_type: str
    error_message: str
    stage: str  # 'input', 'preprocessing', 'ocr', 'pii_detection', 'output'
    diagnostic_info: Dict[str, Any]