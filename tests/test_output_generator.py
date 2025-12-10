"""
Tests for output generation functionality.
"""
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest
from PIL import Image
import numpy as np

from src.output.output_generator import OutputGenerator
from src.models import PIIMatch, PIIResult, ErrorResult


class TestOutputGenerator:
    """Test cases for OutputGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = OutputGenerator()
        self.sample_pii_matches = [
            PIIMatch(
                text="John Doe",
                pii_type="name",
                confidence=0.95,
                start_pos=10,
                end_pos=18
            ),
            PIIMatch(
                text="(555) 123-4567",
                pii_type="phone",
                confidence=0.90,
                start_pos=25,
                end_pos=39
            ),
            PIIMatch(
                text="123 Main St",
                pii_type="address",
                confidence=0.85,
                start_pos=45,
                end_pos=56
            )
        ]
        self.sample_metadata = {
            "ocr_engine": "tesseract",
            "processing_time": 2.5,
            "image_quality_score": 0.8
        }
    
    def test_generate_json_output_success(self):
        """Test successful JSON output generation."""
        original_text = "Patient: John Doe, Phone: (555) 123-4567, Address: 123 Main St"
        
        json_output = self.generator.generate_json_output(
            original_text=original_text,
            pii_matches=self.sample_pii_matches,
            processing_metadata=self.sample_metadata
        )
        
        # Parse the JSON to verify structure
        result = json.loads(json_output)
        
        assert result['success'] is True
        assert result['original_text'] == original_text
        assert len(result['pii_matches']) == 3
        assert 'generated_at' in result
        assert result['processing_metadata'] == self.sample_metadata
        
        # Check PII match structure
        pii_match = result['pii_matches'][0]
        assert pii_match['text'] == "John Doe"
        assert pii_match['type'] == "name"
        assert pii_match['confidence'] == 0.95
        assert pii_match['position']['start'] == 10
        assert pii_match['position']['end'] == 18
    
    def test_generate_json_output_with_redacted_image(self):
        """Test JSON output generation with redacted image path."""
        original_text = "Test text"
        redacted_path = "/path/to/redacted.jpg"
        
        json_output = self.generator.generate_json_output(
            original_text=original_text,
            pii_matches=self.sample_pii_matches,
            processing_metadata=self.sample_metadata,
            redacted_image_path=redacted_path
        )
        
        result = json.loads(json_output)
        assert result['redacted_image_path'] == redacted_path
    
    def test_format_pii_summary(self):
        """Test PII summary generation."""
        summary = self.generator.format_pii_summary(self.sample_pii_matches)
        
        assert summary['total_matches'] == 3
        assert summary['by_type']['name'] == 1
        assert summary['by_type']['phone'] == 1
        assert summary['by_type']['address'] == 1
        
        # Check confidence statistics
        assert summary['confidence_stats']['average'] == pytest.approx(0.9, abs=0.01)
        assert summary['confidence_stats']['min'] == 0.85
        assert summary['confidence_stats']['max'] == 0.95
    
    def test_format_pii_summary_empty(self):
        """Test PII summary with no matches."""
        summary = self.generator.format_pii_summary([])
        
        assert summary['total_matches'] == 0
        assert summary['by_type'] == {}
        assert summary['confidence_stats']['average'] == 0.0
    
    def test_generate_error_output(self):
        """Test error output generation."""
        error = ErrorResult(
            error_type="validation_error",
            error_message="Invalid input format",
            stage="input",
            diagnostic_info={"file_type": "PNG", "expected": "JPEG"}
        )
        
        json_output = self.generator.generate_error_output(error)
        result = json.loads(json_output)
        
        assert result['success'] is False
        assert result['error']['type'] == "validation_error"
        assert result['error']['message'] == "Invalid input format"
        assert result['error']['stage'] == "input"
        assert result['error']['diagnostic_info']['file_type'] == "PNG"
        assert 'generated_at' in result
    
    def test_generate_redacted_image_success(self):
        """Test successful redacted image generation."""
        # Create a temporary test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_input:
            # Create a simple test image
            test_image = Image.new('RGB', (200, 100), color='white')
            test_image.save(temp_input.name, 'JPEG')
            temp_input_path = temp_input.name
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            # Generate redacted image
            result_path = self.generator.generate_redacted_image(
                original_image_path=temp_input_path,
                pii_matches=self.sample_pii_matches,
                output_path=temp_output_path
            )
            
            assert result_path == temp_output_path
            assert os.path.exists(temp_output_path)
            
            # Verify the output is a valid image
            with Image.open(temp_output_path) as img:
                assert img.size == (200, 100)
                assert img.mode == 'RGB'
        
        finally:
            # Clean up temporary files
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
    
    def test_generate_redacted_image_file_not_found(self):
        """Test redacted image generation with missing input file."""
        with pytest.raises(FileNotFoundError):
            self.generator.generate_redacted_image(
                original_image_path="/nonexistent/path.jpg",
                pii_matches=self.sample_pii_matches,
                output_path="/tmp/output.jpg"
            )
    
    def test_generate_redacted_image_invalid_method(self):
        """Test redacted image generation with invalid redaction method."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_input:
            test_image = Image.new('RGB', (200, 100), color='white')
            test_image.save(temp_input.name, 'JPEG')
            temp_input_path = temp_input.name
        
        try:
            with pytest.raises(ValueError, match="Invalid redaction method"):
                self.generator.generate_redacted_image(
                    original_image_path=temp_input_path,
                    pii_matches=self.sample_pii_matches,
                    output_path="/tmp/output.jpg",
                    redaction_method="invalid_method"
                )
        finally:
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    def test_save_output_to_file(self):
        """Test saving JSON output to file."""
        json_data = '{"test": "data"}'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            result_path = self.generator.save_output_to_file(json_data, temp_path)
            
            assert result_path == temp_path
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r') as f:
                saved_data = f.read()
            
            assert saved_data == json_data
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_json_output_structure_consistency(self):
        """Test that JSON output always has consistent structure."""
        # Test with different scenarios
        scenarios = [
            # No PII matches
            ([], "No PII found"),
            # Single match
            ([self.sample_pii_matches[0]], "Single PII match"),
            # Multiple matches
            (self.sample_pii_matches, "Multiple PII matches")
        ]
        
        for pii_matches, description in scenarios:
            json_output = self.generator.generate_json_output(
                original_text="Test text",
                pii_matches=pii_matches,
                processing_metadata=self.sample_metadata
            )
            
            result = json.loads(json_output)
            
            # Verify required fields are always present
            required_fields = [
                'success', 'original_text', 'pii_matches', 
                'pii_summary', 'processing_metadata', 'generated_at'
            ]
            
            for field in required_fields:
                assert field in result, f"Missing field '{field}' in scenario: {description}"
            
            # Verify structure consistency
            assert isinstance(result['pii_matches'], list)
            assert isinstance(result['pii_summary'], dict)
            assert isinstance(result['processing_metadata'], dict)
            assert result['success'] is True