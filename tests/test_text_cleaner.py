"""
Tests for text cleaning functionality.
"""
import pytest
from src.utils.text_cleaner import TextCleaner


class TestTextCleaner:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cleaner = TextCleaner()
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        # Test multiple spaces
        text = "Hello    world   test"
        result = self.cleaner.normalize_whitespace(text)
        assert result == "Hello world test"
        
        # Test leading/trailing whitespace
        text = "  Hello world  "
        result = self.cleaner.normalize_whitespace(text)
        assert result == "Hello world"
        
        # Test newlines and tabs
        text = "Hello\n\nworld\t\ttest"
        result = self.cleaner.normalize_whitespace(text)
        assert result == "Hello world test"
        
        # Test empty string
        assert self.cleaner.normalize_whitespace("") == ""
        assert self.cleaner.normalize_whitespace(None) == ""
    
    def test_fix_common_ocr_errors(self):
        """Test OCR error correction."""
        # Test digit to letter corrections
        text = "0mega 1nsulin 5albutamol"
        result = self.cleaner.fix_common_ocr_errors(text)
        assert "Omega" in result
        assert "Insulin" in result
        assert "Salbutamol" in result
        
        # Test pipe to I correction
        text = "|nsulin"
        result = self.cleaner.fix_common_ocr_errors(text)
        assert result == "Insulin"
        
        # Test rn to m correction (only in middle of words)
        text = "mornring"
        result = self.cleaner.fix_common_ocr_errors(text)
        assert result == "momring"  # Only rn in middle gets replaced
    
    def test_clean_medical_text(self):
        """Test medical-specific text cleaning."""
        # Test dosage formatting
        text = "Take 500 mg twice daily"
        result = self.cleaner.clean_medical_text(text)
        assert "500mg" in result
        
        # Test time formatting
        text = "Take at 8 : 30 am"
        result = self.cleaner.clean_medical_text(text)
        assert "8:30am" in result
        
        # Test tablet formatting
        text = "2 tab daily"
        result = self.cleaner.clean_medical_text(text)
        assert "2 tab" in result
    
    def test_remove_artifacts(self):
        """Test artifact removal."""
        # Test isolated punctuation removal (with spaces around)
        text = "Hello . world ! test"
        result = self.cleaner.remove_artifacts(text)
        assert " . " not in result and " ! " not in result
        
        # Test multiple dashes/underscores
        text = "Hello --- world ___ test"
        result = self.cleaner.remove_artifacts(text)
        assert "---" not in result
        assert "___" not in result
    
    def test_extract_structured_info(self):
        """Test structured information extraction."""
        text = "Paracetamol 500mg twice daily at 8:30am and 8:30pm. Patient DOB: 15/03/1980"
        
        result = self.cleaner.extract_structured_info(text)
        
        # Check medications
        assert len(result['medications']) > 0
        
        # Check dosages
        assert any('500mg' in dosage for dosage in result['dosages'])
        
        # Check times
        assert len(result['times']) > 0
        
        # Check dates
        assert any('15/03/1980' in date for date in result['dates'])
    
    def test_assess_text_quality(self):
        """Test text quality assessment."""
        original = "Take 500 mg paracetamol twice daily"
        cleaned = "Take 500mg paracetamol twice daily"
        
        quality = self.cleaner.assess_text_quality(original, cleaned)
        
        assert 'quality_score' in quality
        assert 0.0 <= quality['quality_score'] <= 1.0
        assert 'word_retention' in quality
        assert 'medical_score' in quality
    
    def test_assess_text_quality_edge_cases(self):
        """Test quality assessment edge cases."""
        # Empty texts
        quality = self.cleaner.assess_text_quality("", "")
        assert quality['quality_score'] == 0.0
        
        # One empty text
        quality = self.cleaner.assess_text_quality("test", "")
        assert quality['quality_score'] == 0.0
        
        quality = self.cleaner.assess_text_quality("", "test")
        assert quality['quality_score'] == 0.0
    
    def test_clean_text_pipeline(self):
        """Test complete text cleaning pipeline."""
        # Test with medical text containing OCR errors
        dirty_text = "  Take  500 mg  paracetam0l   twice   daily  at  8:30 am  "
        
        cleaned_text, metadata = self.cleaner.clean_text(dirty_text)
        
        # Check that text is cleaned
        assert cleaned_text != dirty_text
        assert "500mg" in cleaned_text
        assert "8:30" in cleaned_text and "am" in cleaned_text
        
        # Check metadata
        assert 'steps' in metadata
        assert 'quality' in metadata
        assert 'structured_info' in metadata
        assert len(metadata['steps']) > 0
        
        # Check quality score
        assert 0.0 <= metadata['quality']['quality_score'] <= 1.0
    
    def test_clean_text_empty_input(self):
        """Test cleaning with empty input."""
        cleaned_text, metadata = self.cleaner.clean_text("")
        
        assert cleaned_text == ""
        assert metadata['quality']['quality_score'] == 0.0
    
    def test_medical_terms_recognition(self):
        """Test recognition of medical terms."""
        text = "paracetamol ibuprofen aspirin tablet capsule morning evening"
        
        structured_info = self.cleaner.extract_structured_info(text)
        quality = self.cleaner.assess_text_quality(text, text)
        
        # Should recognize medical terms and give higher medical score
        assert quality['medical_terms_found'] > 0
        assert quality['medical_score'] > 0