"""
Output generation and redaction module for OCR PII Pipeline.
Handles structured JSON output and optional image redaction.
"""
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from src.models import PIIResult, PIIMatch, ErrorResult

logger = logging.getLogger(__name__)


class OutputGenerator:
    """Generates structured output and optional redacted images from PII detection results."""
    
    def __init__(self):
        """Initialize the output generator."""
        self.default_redaction_color = (0, 0, 0)  # Black
        self.default_redaction_opacity = 255  # Fully opaque
        
    def generate_json_output(self, 
                           original_text: str,
                           pii_matches: List[PIIMatch],
                           processing_metadata: Dict[str, Any],
                           redacted_image_path: Optional[str] = None) -> str:
        """
        Generate structured JSON output from PII detection results.
        
        Args:
            original_text: The original extracted text
            pii_matches: List of detected PII matches
            processing_metadata: Metadata about the processing pipeline
            redacted_image_path: Optional path to redacted image
            
        Returns:
            JSON string containing structured results
            
        Raises:
            ValueError: If input data is invalid
            json.JSONEncodeError: If JSON serialization fails
        """
        try:
            # Create PIIResult object
            result = PIIResult(
                original_text=original_text,
                pii_matches=pii_matches,
                processing_metadata=processing_metadata,
                redacted_image_path=redacted_image_path
            )
            
            # Convert to dictionary for JSON serialization
            result_dict = self._pii_result_to_dict(result)
            
            # Add generation timestamp
            result_dict['generated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Serialize to JSON with proper formatting
            json_output = json.dumps(result_dict, indent=2, ensure_ascii=False)
            
            logger.info(f"Generated JSON output with {len(pii_matches)} PII matches")
            return json_output
            
        except Exception as e:
            logger.error(f"Error generating JSON output: {e}")
            raise
    
    def generate_redacted_image(self,
                              original_image_path: str,
                              pii_matches: List[PIIMatch],
                              output_path: str,
                              redaction_method: str = 'black_box') -> str:
        """
        Generate a redacted version of the original image with PII obscured.
        
        Args:
            original_image_path: Path to the original image
            pii_matches: List of PII matches to redact
            output_path: Path where redacted image should be saved
            redaction_method: Method to use for redaction ('black_box', 'blur', 'pixelate')
            
        Returns:
            Path to the generated redacted image
            
        Raises:
            FileNotFoundError: If original image doesn't exist
            ValueError: If redaction method is invalid
            IOError: If image processing fails
        """
        try:
            if not os.path.exists(original_image_path):
                raise FileNotFoundError(f"Original image not found: {original_image_path}")
            
            # Load the original image
            with Image.open(original_image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create a copy for redaction
                redacted_img = img.copy()
                
                # Apply redaction to each PII match
                for pii_match in pii_matches:
                    redacted_img = self._apply_redaction(
                        redacted_img, 
                        pii_match, 
                        redaction_method
                    )
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save the redacted image
                redacted_img.save(output_path, 'JPEG', quality=95)
                
                logger.info(f"Generated redacted image: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error generating redacted image: {e}")
            raise
    
    def format_pii_summary(self, pii_matches: List[PIIMatch]) -> Dict[str, Any]:
        """
        Generate a summary of detected PII by type.
        
        Args:
            pii_matches: List of detected PII matches
            
        Returns:
            Dictionary containing PII summary statistics
        """
        summary = {
            'total_matches': len(pii_matches),
            'by_type': {},
            'confidence_stats': {
                'average': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        }
        
        if not pii_matches:
            return summary
        
        # Count by type
        type_counts = {}
        confidences = []
        
        for match in pii_matches:
            pii_type = match.pii_type
            type_counts[pii_type] = type_counts.get(pii_type, 0) + 1
            confidences.append(match.confidence)
        
        summary['by_type'] = type_counts
        
        # Calculate confidence statistics
        if confidences:
            summary['confidence_stats'] = {
                'average': sum(confidences) / len(confidences),
                'min': min(confidences),
                'max': max(confidences)
            }
        
        return summary
    
    def generate_error_output(self, error: ErrorResult) -> str:
        """
        Generate structured JSON output for error conditions.
        
        Args:
            error: ErrorResult object containing error information
            
        Returns:
            JSON string containing error information
        """
        try:
            error_dict = {
                'success': False,
                'error': {
                    'type': error.error_type,
                    'message': error.error_message,
                    'stage': error.stage,
                    'diagnostic_info': error.diagnostic_info
                },
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            return json.dumps(error_dict, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error generating error output: {e}")
            # Fallback error response
            fallback = {
                'success': False,
                'error': {
                    'type': 'output_generation_error',
                    'message': f'Failed to generate error output: {str(e)}',
                    'stage': 'output',
                    'diagnostic_info': {}
                },
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            return json.dumps(fallback, indent=2)
    
    def _pii_result_to_dict(self, result: PIIResult) -> Dict[str, Any]:
        """Convert PIIResult object to dictionary for JSON serialization."""
        return {
            'success': True,
            'original_text': result.original_text,
            'pii_matches': [
                {
                    'text': match.text,
                    'type': match.pii_type,
                    'confidence': match.confidence,
                    'position': {
                        'start': match.start_pos,
                        'end': match.end_pos
                    }
                }
                for match in result.pii_matches
            ],
            'pii_summary': self.format_pii_summary(result.pii_matches),
            'processing_metadata': result.processing_metadata,
            'redacted_image_path': result.redacted_image_path
        }
    
    def _apply_redaction(self, 
                        image: Image.Image, 
                        pii_match: PIIMatch, 
                        method: str) -> Image.Image:
        """
        Apply redaction to a specific PII match area in the image.
        
        Note: This is a simplified implementation that redacts based on text position.
        In a real-world scenario, you would need OCR bounding box information
        to accurately map text positions to image coordinates.
        """
        if method not in ['black_box', 'blur', 'pixelate']:
            raise ValueError(f"Invalid redaction method: {method}")
        
        # For this implementation, we'll create a simple overlay
        # In practice, you'd need OCR bounding box data to map text positions to image coordinates
        
        draw = ImageDraw.Draw(image)
        
        # Estimate redaction area (this is simplified - real implementation would use OCR bounding boxes)
        img_width, img_height = image.size
        
        # Simple heuristic: assume text is distributed evenly across the image
        # and calculate approximate position based on character positions
        text_length = len(pii_match.text)
        char_width = img_width / 100  # Rough estimate
        char_height = img_height / 50  # Rough estimate
        
        # Calculate approximate bounding box
        x1 = (pii_match.start_pos % 100) * char_width
        y1 = (pii_match.start_pos // 100) * char_height
        x2 = x1 + (text_length * char_width)
        y2 = y1 + char_height
        
        # Ensure coordinates are within image bounds
        x1 = max(0, min(x1, img_width))
        y1 = max(0, min(y1, img_height))
        x2 = max(x1, min(x2, img_width))
        y2 = max(y1, min(y2, img_height))
        
        if method == 'black_box':
            # Draw black rectangle over the PII area
            draw.rectangle([x1, y1, x2, y2], fill=self.default_redaction_color)
        
        elif method == 'blur':
            # For blur, we'd need more sophisticated image processing
            # For now, use a semi-transparent overlay
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([x1, y1, x2, y2], fill=(128, 128, 128, 128))
            image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        
        elif method == 'pixelate':
            # Simple pixelation effect
            draw.rectangle([x1, y1, x2, y2], fill=(128, 128, 128))
        
        return image
    
    def save_output_to_file(self, json_output: str, output_path: str) -> str:
        """
        Save JSON output to a file.
        
        Args:
            json_output: JSON string to save
            output_path: Path where to save the output
            
        Returns:
            Path to the saved file
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_output)
            
            logger.info(f"Saved output to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving output to file: {e}")
            raise