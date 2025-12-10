"""
Tests for the main OCR PII Pipeline orchestrator.
"""
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest
from PIL import Image

from src.pipeline.ocr_pii_pipeline import OCRPIIPipeline
from src.models import PIIMatch


class TestOCRPIIPipeline:
    """Test cases for OCRPIIPipeline class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = OCRPIIPipeline()
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        assert self.pipeline.preprocessor is not None
        assert self.pipeline.ocr_engine is not None
        assert self.pipeline.text_cleaner is not None
        assert self.pipeline.pii_detector is not None
        assert self.pipeline.output_generator is not None
    
    def test_process_image_file_not_found(self):
        """Test processing with non-existent file."""
        result = self.pipeline.process_image("/nonexistent/file.jpg")
        
        assert not result.processing_metadata.get('success', True)
        assert 'error_message' in result.processing_metadata
        assert 'FileNotFoundError' in str(result.processing_metadata['error_message']) or 'not found' in result.processing_metadata['error_message'].lower()
    
    def test_process_image_invalid_format(self):
        """Test processing with invalid file format."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            result = self.pipeline.process_image(temp_path)
            
            assert not result.processing_metadata.get('success', True)
            assert 'error_message' in result.processing_metadata
            assert 'Invalid file format' in result.processing_metadata['error_message']
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('src.pipeline.ocr_pii_pipeline.ImagePreprocessor')
    @patch('src.pipeline.ocr_pii_pipeline.OCREngine')
    @patch('src.pipeline.ocr_pii_pipeline.TextCleaner')
    @patch('src.pipeline.ocr_pii_pipeline.PIIDetector')
    def test_process_image_success(self, mock_pii_detector, mock_text_cleaner, 
                                  mock_ocr_engine, mock_preprocessor):
        """Test successful image processing."""
        # Create a test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            test_image = Image.new('RGB', (100, 100), color='white')
            test_image.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Mock the pipeline components
            mock_preprocessor_instance = mock_preprocessor.return_value
            mock_preprocessor_instance.preprocess.return_value = (
                MagicMock(), 
                {'preprocessing_steps': ['contrast_enhancement']}
            )
            
            mock_ocr_instance = mock_ocr_engine.return_value
            mock_ocr_instance.extract_with_confidence.return_value = (
                "Test text", 
                0.95, 
                {'selected_engine': 'tesseract'}
            )
            
            mock_cleaner_instance = mock_text_cleaner.return_value
            mock_cleaner_instance.clean_text.return_value = ("Test text", {"cleaned": True})
            mock_cleaner_instance.assess_text_quality.return_value = {'overall_quality': 0.9}
            
            mock_detector_instance = mock_pii_detector.return_value
            mock_detector_instance.detect_all_pii.return_value = [
                PIIMatch("John Doe", "name", 0.95, 0, 8)
            ]
            
            # Create new pipeline instance with mocked components
            pipeline = OCRPIIPipeline()
            pipeline.preprocessor = mock_preprocessor_instance
            pipeline.ocr_engine = mock_ocr_instance
            pipeline.text_cleaner = mock_cleaner_instance
            pipeline.pii_detector = mock_detector_instance
            
            # Process the image
            result = pipeline.process_image(temp_path)
            
            # Verify results
            assert result.processing_metadata.get('success', False)
            assert result.original_text == "Test text"
            assert len(result.pii_matches) == 1
            assert result.pii_matches[0].text == "John Doe"
            
            # Verify metadata structure
            assert 'total_duration_seconds' in result.processing_metadata
            assert 'processing_stages' in result.processing_metadata
            assert 'preprocessing' in result.processing_metadata
            assert 'ocr' in result.processing_metadata
            assert 'text_cleaning' in result.processing_metadata
            assert 'pii_detection' in result.processing_metadata
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_generate_json_output(self):
        """Test JSON output generation."""
        # Create a mock result
        from src.models import PIIResult
        
        result = PIIResult(
            original_text="Test text",
            pii_matches=[PIIMatch("John Doe", "name", 0.95, 0, 8)],
            processing_metadata={"test": "data"},
            redacted_image_path=None
        )
        
        json_output = self.pipeline.generate_json_output(result)
        
        assert isinstance(json_output, str)
        assert "Test text" in json_output
        assert "John Doe" in json_output
        assert "success" in json_output
    
    def test_process_batch(self):
        """Test batch processing."""
        # Create test images
        image_paths = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                test_image = Image.new('RGB', (100, 100), color='white')
                test_image.save(temp_file.name, 'JPEG')
                image_paths.append(temp_file.name)
        
        try:
            results = self.pipeline.process_batch(image_paths)
            
            assert len(results) == 2
            assert all(path in results for path in image_paths)
            
            # All results should have processing metadata
            for result in results.values():
                assert 'processing_metadata' in result.__dict__
        
        finally:
            for path in image_paths:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_save_results(self):
        """Test saving results to files."""
        from src.models import PIIResult
        
        result = PIIResult(
            original_text="Test text",
            pii_matches=[PIIMatch("John Doe", "name", 0.95, 0, 8)],
            processing_metadata={"test": "data"},
            redacted_image_path=None
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            saved_files = self.pipeline.save_results(result, temp_dir, "test")
            
            assert 'json' in saved_files
            assert os.path.exists(saved_files['json'])
            
            # Verify JSON file content
            with open(saved_files['json'], 'r') as f:
                content = f.read()
                assert "Test text" in content
                assert "John Doe" in content