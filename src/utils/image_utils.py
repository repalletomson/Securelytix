"""
Utility functions for image processing and validation.
"""
import os
from PIL import Image
import numpy as np
from typing import Tuple, Optional


def validate_image_format(image_path: str) -> bool:
    """Validate that the image is in JPEG format."""
    try:
        with Image.open(image_path) as img:
            return img.format == 'JPEG'
    except Exception:
        return False


def get_image_info(image_path: str) -> dict:
    """Get basic information about an image file."""
    try:
        with Image.open(image_path) as img:
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'file_size': os.path.getsize(image_path)
            }
    except Exception as e:
        return {'error': str(e)}


def save_processed_image(image: np.ndarray, output_path: str) -> bool:
    """Save processed image to file."""
    try:
        # Convert BGR to RGB for PIL
        if len(image.shape) == 3:
            image_rgb = image[:, :, ::-1]  # BGR to RGB
        else:
            image_rgb = image
        
        pil_image = Image.fromarray(image_rgb)
        pil_image.save(output_path, 'JPEG', quality=95)
        return True
    except Exception:
        return False


def calculate_image_quality_score(image: np.ndarray) -> float:
    """Calculate a simple image quality score based on contrast and sharpness."""
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = np.mean(image, axis=2)
        else:
            gray = image
        
        # Calculate contrast (standard deviation of pixel values)
        contrast = np.std(gray)
        
        # Calculate sharpness using Laplacian variance
        laplacian = np.abs(np.gradient(gray)).mean()
        
        # Combine metrics (normalized to 0-1 range)
        quality_score = min(1.0, (contrast / 50.0 + laplacian / 10.0) / 2.0)
        
        return quality_score
    except Exception:
        return 0.0