"""
Qwen-VL model wrapper for vision-language tasks
"""
import torch
import logging
import os
import tempfile
from PIL import Image
import re
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer
import time

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

class InternVL:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.transform = None
        self.model_healthy = False
        self.clip_processor = None
        self.clip_model = None
        self._initialize_models()

    def _initialize_models(self):
        """Initialize InternVL2 model"""
        try:
            # Initialize tokenizer first
            self.tokenizer = AutoTokenizer.from_pretrained(
                "OpenGVLab/InternVL2-4B", 
                trust_remote_code=True,
                use_fast=False
            )
            
            if not self.tokenizer:
                raise RuntimeError("Failed to initialize tokenizer")
                
            # Initialize model
            self.model = AutoModel.from_pretrained(
                "OpenGVLab/InternVL2-4B",
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
                use_flash_attn=True,
                trust_remote_code=True
            ).eval()
            
            if not self.model:
                raise RuntimeError("Failed to initialize model")
                
            if torch.cuda.is_available():
                self.model = self.model.cuda()
                
            self.transform = self._build_transform(input_size=448)
            
            if not self.transform:
                raise RuntimeError("Failed to initialize transform")
                
            logging.info("InternVL2 model initialized successfully")
            self.model_healthy = True
            
        except Exception as e:
            logging.error(f"Failed to initialize InternVL2 model: {e}")
            self.model_healthy = False
            raise RuntimeError(f"InternVL2 initialization failed: {str(e)}")

    def _build_transform(self, input_size):
        """Build transform pipeline for InternVL2"""
        return T.Compose([
            T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
            T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])

    def understand_scene(self, image, context=None) -> Dict[str, Any]:
        """
        Analyze scene using InternVL2 model.
        
        Args:
            image: PIL Image or path to image
            context: Optional context or prompt for analysis
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Process image
            pixel_values = self._preprocess_image(image)
            
            # Format prompt based on context
            prompt = self._format_prompt(context)

            # Generate response using InternVL2
            generation_config = dict(max_new_tokens=1024, do_sample=True)
            response, _ = self.model.chat(
                self.tokenizer,
                pixel_values,
                prompt,
                generation_config
            )

            return {
                'status': 'success',
                'description': response,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logging.error(f"Scene understanding error: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'fallback_description': 'Unable to analyze image content'
            }

    def _preprocess_image(self, image, max_num=12):
        """Preprocess image for InternVL2"""
        if isinstance(image, str):
            image = Image.open(image).convert('RGB')
        elif not isinstance(image, Image.Image):
            raise ValueError(f"Expected PIL Image or path, got {type(image)}")

        # Process image using dynamic preprocessing
        processed_images = self._dynamic_preprocess(image, max_num=max_num)
        pixel_values = [self.transform(img) for img in processed_images]
        pixel_values = torch.stack(pixel_values)
        
        if torch.cuda.is_available():
            pixel_values = pixel_values.to(torch.bfloat16).cuda()
        else:
            pixel_values = pixel_values.to(torch.bfloat16)
            
        return pixel_values

    def _dynamic_preprocess(self, image, min_num=1, max_num=12, image_size=448, use_thumbnail=True):
        """Dynamic preprocessing for InternVL2"""
        orig_width, orig_height = image.size
        aspect_ratio = orig_width / orig_height

        # Calculate target ratios
        target_ratios = set(
            (i, j) for n in range(min_num, max_num + 1) 
            for i in range(1, n + 1) 
            for j in range(1, n + 1) 
            if i * j <= max_num and i * j >= min_num
        )
        target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

        # Find closest aspect ratio
        best_ratio = self._find_closest_aspect_ratio(
            aspect_ratio, target_ratios, orig_width, orig_height, image_size
        )

        # Calculate dimensions and process image
        target_width = image_size * best_ratio[0]
        target_height = image_size * best_ratio[1]
        blocks = best_ratio[0] * best_ratio[1]

        resized_img = image.resize((target_width, target_height))
        processed_images = []
        
        for i in range(blocks):
            box = (
                (i % (target_width // image_size)) * image_size,
                (i // (target_width // image_size)) * image_size,
                ((i % (target_width // image_size)) + 1) * image_size,
                ((i // (target_width // image_size)) + 1) * image_size
            )
            split_img = resized_img.crop(box)
            processed_images.append(split_img)

        if use_thumbnail and len(processed_images) != 1:
            thumbnail_img = image.resize((image_size, image_size))
            processed_images.append(thumbnail_img)
            
        return processed_images

    def _find_closest_aspect_ratio(self, aspect_ratio, target_ratios, width, height, image_size):
        """Find closest aspect ratio from target ratios"""
        best_ratio_diff = float('inf')
        best_ratio = (1, 1)
        area = width * height
        
        for ratio in target_ratios:
            target_aspect_ratio = ratio[0] / ratio[1]
            ratio_diff = abs(aspect_ratio - target_aspect_ratio)
            
            if ratio_diff < best_ratio_diff:
                best_ratio_diff = ratio_diff
                best_ratio = ratio
            elif ratio_diff == best_ratio_diff:
                if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                    best_ratio = ratio
                    
        return best_ratio

    def _format_prompt(self, context) -> str:
        """Format context into a prompt for the model"""
        if isinstance(context, str):
            return f"<image>\n{context}"
        elif isinstance(context, dict):
            context_str = context.get('question', '')
            focus = context.get('focus', '')
            prompt = f"<image>\n{context_str}"
            if focus:
                prompt += f"\nFocus on: {focus}"
            return prompt
        else:
            return "<image>\nDescribe what you see in this image in detail, focusing on UI elements, buttons, and interactive components."

    def perceive_scene(self, image, context=None):
        """
        Main entry point for scene perception using InternVL2.
        
        Args:
            image: Input image (PIL Image, numpy array, or path)
            context: Optional context for scene understanding
            
        Returns:
            dict: Scene perception results
        """
        try:
            # Validate and process image
            if isinstance(image, dict) and 'frame' in image:
                image = image['frame']
                
            # Process image
            pixel_values = self._preprocess_image(image)
            
            # Generate base scene understanding
            scene_result = self.understand_scene(image, context)
            
            return {
                'status': 'success',
                'scene': scene_result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logging.error(f"Error in scene perception: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }

    def parse_coordinates(self, text: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Parses coordinates from a given text string.

        Args:
            text (str): The text containing coordinate information.

        Returns:
            Optional[Tuple[int, int, int, int]]: A tuple of coordinates if found, else None.
        """
        try:
            import re
            pattern = r'coordinates:?\s*\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return tuple(map(int, match.groups()))
        except Exception as e:
            logging.error(f"Error parsing coordinates: {e}")
        return None
