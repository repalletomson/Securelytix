"""
Tests for PII detection functionality.
"""
import pytest
from src.pii_detection.pii_detector import PIIDetector
from src.models import PIIMatch


class TestPIIDetector:
    """Test cases for PIIDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PIIDetector()
    
    def test_detect_names_with_title(self):
        """Test name detection with titles."""
        text = "Patient: Dr. John Smith was seen today."
        matches = self.detector.detect_names(text)
        
        assert len(matches) >= 1
        assert any(match.pii_type == 'name' for match in matches)
        # Check that we found "John Smith"
        name_texts = [match.text for match in matches]
        assert any('John Smith' in name_text for name_text in name_texts)
    
    def test_detect_addresses_with_street(self):
        """Test address detection with street numbers."""
        text = "Address: 123 Main Street, Anytown, CA 90210"
        matches = self.detector.detect_addresses(text)
        
        assert len(matches) >= 1
        assert any(match.pii_type == 'address' for match in matches)
    
    def test_detect_phone_numbers(self):
        """Test phone number detection."""
        text = "Phone: (555) 123-4567"
        matches = self.detector.detect_phone_numbers(text)
        
        assert len(matches) >= 1
        assert any(match.pii_type == 'phone' for match in matches)
    
    def test_detect_medical_ids(self):
        """Test medical ID detection."""
        text = "MRN: ABC123456"
        matches = self.detector.detect_medical_ids(text)
        
        assert len(matches) >= 1
        assert any(match.pii_type == 'medical_id' for match in matches)
    
    def test_detect_ssns(self):
        """Test SSN detection."""
        text = "SSN: 123-45-6789"
        matches = self.detector.detect_ssns(text)
        
        assert len(matches) >= 1
        assert any(match.pii_type == 'ssn' for match in matches)
    
    def test_detect_all_pii(self):
        """Test comprehensive PII detection."""
        text = """
        Patient: John Doe
        Address: 123 Main St, Anytown, CA 90210
        Phone: (555) 123-4567
        MRN: MED123456
        SSN: 123-45-6789
        """
        matches = self.detector.detect_all_pii(text)
        
        # Should detect multiple types of PII
        pii_types = {match.pii_type for match in matches}
        assert len(pii_types) >= 3  # At least 3 different types
        
        # All matches should have confidence scores
        assert all(0 <= match.confidence <= 1.0 for match in matches)
        
        # Matches should be sorted by position
        positions = [match.start_pos for match in matches]
        assert positions == sorted(positions)