"""
Image preprocessing module for OCR pipeline.
Handles contrast enhancement, noise reduction, and orientation correction.
"""
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles image preprocessing operations to improve OCR accuracy."""
    
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    def load_image(self, image_path: str) -> np.ndarray:
        """Load and validate JPEG image."""
        try:
            # Load with PIL first to validate format
            pil_image = Image.open(image_path)
            if pil_image.format != 'JPEG':
                raise ValueError(f"Expected JPEG format, got {pil_image.format}")
            
            # Convert to OpenCV format
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            return image
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            raise
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        try:
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            
            # Apply CLAHE to L channel
            l_channel = self.clahe.apply(l_channel)
            
            # Merge channels back
            enhanced_lab = cv2.merge([l_channel, a_channel, b_channel])
            enhanced_image = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
            return enhanced_image
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}")
            return image
    
    def reduce_noise(self, image: np.ndarray) -> np.ndarray:
        """Apply noise reduction filters."""
        try:
            # Apply bilateral filter to reduce noise while preserving edges
            denoised = cv2.bilateralFilter(image, 9, 75, 75)
            
            # Apply morphological operations to clean up text
            gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            cleaned = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to BGR
            cleaned_bgr = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
            
            return cleaned_bgr
        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}")
            return image
    
    def detect_skew_angle(self, image: np.ndarray) -> float:
        """Detect skew angle using Hough line transform."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detect lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = np.degrees(theta) - 90
                    if abs(angle) < 45:  # Only consider reasonable skew angles
                        angles.append(angle)
                
                if angles:
                    # Return median angle to avoid outliers
                    return np.median(angles)
            
            return 0.0
        except Exception as e:
            logger.warning(f"Skew detection failed: {e}")
            return 0.0
    
    def correct_orientation(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct image orientation/skew."""
        try:
            skew_angle = self.detect_skew_angle(image)
            
            # Only correct if skew is significant (> 0.5 degrees)
            if abs(skew_angle) > 0.5:
                height, width = image.shape[:2]
                center = (width // 2, height // 2)
                
                # Create rotation matrix
                rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                
                # Calculate new image dimensions
                cos_angle = abs(rotation_matrix[0, 0])
                sin_angle = abs(rotation_matrix[0, 1])
                new_width = int((height * sin_angle) + (width * cos_angle))
                new_height = int((height * cos_angle) + (width * sin_angle))
                
                # Adjust rotation matrix for new center
                rotation_matrix[0, 2] += (new_width / 2) - center[0]
                rotation_matrix[1, 2] += (new_height / 2) - center[1]
                
                # Apply rotation
                corrected = cv2.warpAffine(image, rotation_matrix, (new_width, new_height), 
                                         flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                
                logger.info(f"Corrected skew angle: {skew_angle:.2f} degrees")
                return corrected
            
            return image
        except Exception as e:
            logger.warning(f"Orientation correction failed: {e}")
            return image
    
    def preprocess(self, image_path: str) -> Tuple[np.ndarray, dict]:
        """
        Complete preprocessing pipeline.
        
        Returns:
            Tuple of (processed_image, metadata)
        """
        metadata = {
            'original_path': image_path,
            'preprocessing_steps': [],
            'skew_corrected': False,
            'contrast_enhanced': True,
            'noise_reduced': True
        }
        
        try:
            # Load image
            image = self.load_image(image_path)
            original_shape = image.shape
            metadata['original_shape'] = original_shape
            
            # Step 1: Enhance contrast
            image = self.enhance_contrast(image)
            metadata['preprocessing_steps'].append('contrast_enhancement')
            
            # Step 2: Reduce noise
            image = self.reduce_noise(image)
            metadata['preprocessing_steps'].append('noise_reduction')
            
            # Step 3: Correct orientation
            skew_angle = self.detect_skew_angle(image)
            if abs(skew_angle) > 0.5:
                image = self.correct_orientation(image)
                metadata['skew_corrected'] = True
                metadata['skew_angle'] = skew_angle
                metadata['preprocessing_steps'].append('orientation_correction')
            
            metadata['final_shape'] = image.shape
            logger.info(f"Preprocessing completed for {image_path}")
            
            return image, metadata
            
        except Exception as e:
            logger.error(f"Preprocessing failed for {image_path}: {e}")
            raise