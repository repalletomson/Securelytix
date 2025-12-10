"""
Tests for image preprocessing functionality.
"""
import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from src.preprocessing.image_preprocessor import ImagePreprocessor
from src.utils.image_utils import validate_image_format, calculate_image_quality_score


class TestImagePreprocessor:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.preprocessor = ImagePreprocessor()
        # Create a simple test image
        self.test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
    
    def test_enhance_contrast(self):
        """Test contrast enhancement functionality."""
        enhanced = self.preprocessor.enhance_contrast(self.test_image)
        
        assert enhanced.shape == self.test_image.shape
        assert enhanced.dtype == self.test_image.dtype
        # Enhanced image should be different from original
        assert not np.array_equal(enhanced, self.test_image)
    
    def test_reduce_noise(self):
        """Test noise reduction functionality."""
        # Add some noise to test image
        noisy_image = self.test_image.copy()
        noise = np.random.randint(-20, 20, self.test_image.shape, dtype=np.int16)
        noisy_image = np.clip(noisy_image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        denoised = self.preprocessor.reduce_noise(noisy_image)
        
        assert denoised.shape == noisy_image.shape
        assert denoised.dtype == noisy_image.dtype
    
    def test_detect_skew_angle(self):
        """Test skew angle detection."""
        angle = self.preprocessor.detect_skew_angle(self.test_image)
        
        # Should return a float
        assert isinstance(angle, float)
        # Angle should be reasonable
        assert -45 <= angle <= 45
    
    def test_correct_orientation(self):
        """Test orientation correction."""
        corrected = self.preprocessor.correct_orientation(self.test_image)
        
        assert corrected.dtype == self.test_image.dtype
        # Should return an image (dimensions might change due to rotation)
        assert len(corrected.shape) == 3
    
    @patch('cv2.imread')
    @patch('PIL.Image.open')
    def test_load_image_success(self, mock_pil_open, mock_cv_imread):
        """Test successful image loading."""
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.format = 'JPEG'
        mock_pil_open.return_value = mock_img
        
        # Mock OpenCV imread
        mock_cv_imread.return_value = self.test_image
        
        result = self.preprocessor.load_image('test.jpg')
        
        assert np.array_equal(result, self.test_image)
    
    @patch('PIL.Image.open')
    def test_load_image_invalid_format(self, mock_pil_open):
        """Test loading non-JPEG image raises error."""
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_pil_open.return_value = mock_img
        
        with pytest.raises(ValueError, match="Expected JPEG format"):
            self.preprocessor.load_image('test.png')


class TestImageUtils:
    
    def test_calculate_image_quality_score(self):
        """Test image quality score calculation."""
        # Test with a simple image
        test_image = np.ones((50, 50, 3), dtype=np.uint8) * 128
        score = calculate_image_quality_score(test_image)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_calculate_image_quality_score_grayscale(self):
        """Test quality score with grayscale image."""
        test_image = np.ones((50, 50), dtype=np.uint8) * 128
        score = calculate_image_quality_score(test_image)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0