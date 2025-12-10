"""
Tests for OCR engine functionality.
"""
import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from src.ocr.ocr_engine import OCREngine


class TestOCREngine:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ocr_engine = OCREngine()
        # Create a simple test image with text-like patterns
        self.test_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
        # Add some black rectangles to simulate text
        cv2.rectangle(self.test_image, (10, 30), (50, 50), (0, 0, 0), -1)
        cv2.rectangle(self.test_image, (60, 30), (100, 50), (0, 0, 0), -1)
    
    def test_initialization(self):
        """Test OCR engine initialization."""
        engine = OCREngine(preferred_engine='tesseract')
        assert engine.preferred_engine == 'tesseract'
        
        engine = OCREngine(preferred_engine='easyocr')
        assert engine.preferred_engine == 'easyocr'
    
    def test_preprocess_for_ocr(self):
        """Test OCR-specific preprocessing."""
        processed = self.ocr_engine._preprocess_for_ocr(self.test_image)
        
        # Should return grayscale binary image
        assert len(processed.shape) == 2
        assert processed.dtype == np.uint8
        # Should contain only 0 and 255 values (binary)
        unique_values = np.unique(processed)
        assert len(unique_values) <= 2
    
    @patch('pytesseract.image_to_data')
    def test_extract_text_tesseract_success(self, mock_tesseract):
        """Test successful Tesseract text extraction."""
        # Mock Tesseract response
        mock_tesseract.return_value = {
            'text': ['', 'Hello', 'World', ''],
            'conf': [0, 85, 90, 0]
        }
        
        text, confidence = self.ocr_engine.extract_text_tesseract(self.test_image)
        
        assert text == 'Hello World'
        assert 0.8 < confidence < 1.0  # Should be around 87.5/100
    
    @patch('pytesseract.image_to_data')
    def test_extract_text_tesseract_low_confidence(self, mock_tesseract):
        """Test Tesseract with low confidence words."""
        # Mock Tesseract response with low confidence
        mock_tesseract.return_value = {
            'text': ['', 'Hello', 'Wrld', ''],
            'conf': [0, 85, 25, 0]  # Second word has low confidence
        }
        
        text, confidence = self.ocr_engine.extract_text_tesseract(self.test_image)
        
        # Should only include high-confidence word
        assert text == 'Hello'
        assert confidence == 0.85
    
    def test_extract_text_tesseract_failure(self):
        """Test Tesseract failure handling."""
        with patch('pytesseract.image_to_data', side_effect=Exception("OCR failed")):
            text, confidence = self.ocr_engine.extract_text_tesseract(self.test_image)
            
            assert text == ""
            assert confidence == 0.0
    
    def test_extract_text_easyocr_no_reader(self):
        """Test EasyOCR when reader is not available."""
        self.ocr_engine.easyocr_reader = None
        
        text, confidence = self.ocr_engine.extract_text_easyocr(self.test_image)
        
        assert text == ""
        assert confidence == 0.0
    
    def test_extract_text_easyocr_success(self):
        """Test successful EasyOCR text extraction."""
        # Mock EasyOCR reader
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[10, 30], [50, 30], [50, 50], [10, 50]], 'Hello', 0.85),
            ([[60, 30], [100, 30], [100, 50], [60, 50]], 'World', 0.90)
        ]
        
        self.ocr_engine.easyocr_reader = mock_reader
        
        text, confidence = self.ocr_engine.extract_text_easyocr(self.test_image)
        
        assert text == 'Hello World'
        assert confidence == 0.875  # Average of 0.85 and 0.90
    
    def test_clean_extracted_text(self):
        """Test text cleaning functionality."""
        # Test whitespace normalization
        dirty_text = "  Hello    World  \n\n  "
        cleaned = self.ocr_engine._clean_extracted_text(dirty_text)
        assert cleaned == "Hello World"
        
        # Test empty text
        assert self.ocr_engine._clean_extracted_text("") == ""
        assert self.ocr_engine._clean_extracted_text(None) == ""
    
    def test_extract_with_confidence_tesseract_primary(self):
        """Test extraction with Tesseract as primary engine."""
        with patch.object(self.ocr_engine, 'extract_text_tesseract', return_value=('Hello World', 0.85)):
            text, confidence, metadata = self.ocr_engine.extract_with_confidence(self.test_image)
            
            assert text == 'Hello World'
            assert confidence == 0.85
            assert metadata['primary_engine'] == 'tesseract'
            assert 'tesseract' in metadata['engines_tried']
            assert not metadata['fallback_used']
    
    def test_extract_with_confidence_fallback(self):
        """Test extraction with fallback mechanism."""
        # Mock Tesseract to return low confidence
        with patch.object(self.ocr_engine, 'extract_text_tesseract', return_value=('', 0.1)), \
             patch.object(self.ocr_engine, 'extract_text_easyocr', return_value=('Hello World', 0.8)):
            
            # Ensure EasyOCR reader is available for fallback
            self.ocr_engine.easyocr_reader = MagicMock()
            
            text, confidence, metadata = self.ocr_engine.extract_with_confidence(self.test_image)
            
            assert text == 'Hello World'
            assert confidence == 0.8
            assert metadata['fallback_used']
            assert len(metadata['engines_tried']) == 2
    
    def test_extract_text_simple_interface(self):
        """Test simple text extraction interface."""
        with patch.object(self.ocr_engine, 'extract_with_confidence', return_value=('Hello World', 0.85, {})):
            text = self.ocr_engine.extract_text(self.test_image)
            assert text == 'Hello World'