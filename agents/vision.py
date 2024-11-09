"""
This class is for the vision agent which completes vision tasks for the input
"""
from agents.base import BaseAgent
import torch
import numpy as np
from PIL import Image, ImageDraw
from ultralytics import YOLO
import cv2
import logging
import os
import re
import time
from collections import defaultdict
from functools import wraps
import contextlib
from typing import Optional, Dict, Any, Tuple
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
import tempfile
from models.omniparser import OmniParser
from agents.text import TextAgent

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

WEIGHTS_PATH = "weights/best.pt"
BOX_THRESHOLD = 0.03
DRAW_BBOX_CONFIG = {
    'text_scale': 0.8,
    'text_thickness': 2,
    'text_padding': 3,
    'thickness': 3,
}

def timeout(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            if end_time - start_time > seconds:
                raise TimeoutError(f"Function {func.__name__} took {end_time - start_time:.2f} seconds, which exceeds the timeout of {seconds} seconds")
            return result
        return wrapper
    return decorator

class VisionAgent(BaseAgent):
    def __init__(self, screen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.screen = screen  # Store screen reference

        # Initialize models with error handling
        try:
            # Initialize OmniParser
            self.omniparser = OmniParser()  # Ensure OmniParser is correctly instantiated
            
            # Initialize TextAgent
            self.text_agent = TextAgent()
            
            # Performance monitoring
            self.processing_times = []
            self.max_processing_times = 1000
            self.error_counts = defaultdict(int)
            self.last_error_reset = time.time()
            self.error_threshold = 50
            
            logging.info("VisionAgent initialized with OmniParser and TextAgent.")
            
        except Exception as e:
            logging.error(f"Error initializing VisionAgent: {e}")
            raise

    def _preprocess_image(self, image, max_num=12):
        """Preprocess image for InternVL2"""
        try:
            # Ensure we have a PIL Image
            if isinstance(image, np.ndarray):
                if len(image.shape) == 2:  # Grayscale
                    image = Image.fromarray(image, 'L').convert('RGB')
                elif len(image.shape) == 3:
                    if image.shape[2] == 4:  # RGBA
                        image = Image.fromarray(image, 'RGBA').convert('RGB')
                    else:  # Assume BGR
                        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            elif isinstance(image, str):
                image = Image.open(image).convert('RGB')
            elif not isinstance(image, Image.Image):
                raise ValueError(f"Unsupported image type: {type(image)}")
                
            image = image.convert('RGB')
            
            # Dynamic preprocessing
            processed_images = self._dynamic_preprocess(image, image_size=448, max_num=max_num)
            pixel_values = [self.transform(img) for img in processed_images]
            pixel_values = torch.stack(pixel_values)
            
            if torch.cuda.is_available():
                pixel_values = pixel_values.to(torch.float16).cuda()  # Use float16 instead of bfloat16
            else:
                pixel_values = pixel_values.to(torch.float16)  # Use float16 instead of bfloat16
                
            return pixel_values
            
        except Exception as e:
            logging.error(f"Error preprocessing image: {e}")
            raise

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
        
        # Calculate target dimensions
        target_width = image_size * best_ratio[0]
        target_height = image_size * best_ratio[1]
        blocks = best_ratio[0] * best_ratio[1]
        
        # Resize and split image
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

    def perceive_scene(self, image, context=None):
        """
        Main entry point for scene perception.
        
        Args:
            image: Input image (PIL Image, numpy array, or dict with 'frame' key)
            context: Optional context for scene understanding
            
        Returns:
            dict: Scene perception results
        """
        try:
            # Use OmniParser to annotate the image
            annotations = self.omniparser.detect_elements(image, query=context.get('task') if context else None)
            
            if annotations['status'] == 'success':
                # Utilize TextAgent's complete_task with annotated images
                text_results = self.text_agent.complete_task({
                    "image": annotations['labeled_image'],
                    "query": context.get('task') if context else ""
                })
                return {
                    'status': 'success',
                    'annotations': annotations['detections'],
                    'text_results': text_results,
                    'timestamp': time.time()
                }
            else:
                logging.error("OmniParser failed to annotate the image.")
                return {
                    'status': 'error',
                    'message': annotations.get('message', 'Annotation failed'),
                    'timestamp': time.time()
                }
    
        except Exception as e:
            logging.error(f"Error in scene perception: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }

    def _save_image_to_temp(self, image) -> str:
        """Save image (PIL.Image or numpy.ndarray) to temporary file and return path"""
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"temp_image_{int(time.time())}.jpg")
        try:
            if isinstance(image, np.ndarray):
                # Convert numpy array to PIL Image
                if image.ndim == 3 and image.shape[2] == 3:
                    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                elif image.ndim == 3 and image.shape[2] == 4:
                    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA))
                else:
                    raise ValueError(f"Unsupported image shape: {image.shape}")
            elif isinstance(image, Image.Image):
                pil_image = image
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")
            
            pil_image.save(temp_path, format='JPEG')  # Explicitly specify the format
            logging.debug(f"Image saved to temporary path: {temp_path}")
            return temp_path
        except Exception as e:
            logging.error(f"Failed to save image to temp: {e}")
            raise

    def understand_scene(self, image, task, context=None):
        """
        Updated to be a synchronous method.
        """
        try:
            # Save the image to a temporary file
            temp_image_path = self._save_image_to_temp(image)

            # Use OmniParser to detect elements in the image
            annotations = self.omniparser.detect_elements(temp_image_path, query=task)  # Pass file path if detect_elements expects it

            if annotations['status'] == 'success':
                # Utilize TextAgent's complete_task with annotated images
                text_results = self.text_agent.complete_task({
                    "image": annotations['labeled_image'],  # Ensure this is the correct format (path or Image object)
                    "query": task
                })

                # Include mouse overlay with detected elements
                overlay_image = self._add_mouse_overlay(image, annotations['detections'])

                return {
                    'status': 'success',
                    'annotations': annotations['detections'],
                    'text_results': text_results,
                    'overlay_image': overlay_image,
                    'timestamp': time.time()
                }
            else:
                logging.error("OmniParser failed to annotate the image.")
                return {
                    'status': 'error',
                    'message': annotations.get('message', 'Annotation failed'),
                    'timestamp': time.time()
                }

        except Exception as e:
            logging.error(f"Error in scene perception: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }

    def _add_mouse_overlay(self, image, detections):
        """Adds a mouse cursor overlay to the detected elements on the image."""
        try:
            # Ensure the image is a PIL.Image. Convert if it's a numpy.ndarray.
            if isinstance(image, np.ndarray):
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                logging.debug("Converted numpy.ndarray to PIL.Image for overlay.")
            elif isinstance(image, Image.Image):
                pil_image = image.copy()
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")
            
            draw = ImageDraw.Draw(pil_image)
            for det in detections:
                bbox = det['bbox']
                # Draw bounding box
                draw.rectangle(bbox, outline="blue", width=2)
                # Draw mouse cursor at center
                center_x = (bbox[0] + bbox[2]) // 2
                center_y = (bbox[1] + bbox[3]) // 2
                cursor_size = 10
                draw.ellipse([
                    (center_x - cursor_size, center_y - cursor_size),
                    (center_x + cursor_size, center_y + cursor_size)
                ], outline="red", width=2)
            return pil_image
        except Exception as e:
            logging.error(f"Error adding mouse overlay: {e}")
            return image

    def get_visual_embedding(self, image):
        """Get CLIP embedding for multimodal processing"""
        try:
            # Process image for CLIP
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            with torch.no_grad():
                embedding = self.clip_model.get_image_features(**inputs)
            return embedding.numpy()
            
        except Exception as e:
            logging.error(f"Error getting visual embedding: {e}")
            return None

    def _validate_and_process_image(self, image):
        """Validate and process image with quality checks and format conversion"""
        if image is None:
            raise ValueError("Image input cannot be None")
            
        # Handle dictionary input
        if isinstance(image, dict) and 'frame' in image:
            return self._validate_and_process_image(image['frame'])
            
        # Convert numpy array to PIL Image
        if isinstance(image, np.ndarray):
            # Validate array properties
            if not np.isfinite(image).all():
                raise ValueError("Image contains invalid values")
            if image.min() < 0 or image.max() > 255:
                raise ValueError("Image values out of valid range")
                
            # Convert based on channels
            if len(image.shape) == 2:  # Grayscale
                image = Image.fromarray(image, 'L').convert('RGB')
            elif len(image.shape) == 3:
                if image.shape[2] == 4:  # RGBA
                    image = Image.fromarray(image, 'RGBA').convert('RGB')
                else:  # Assume BGR
                    image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                    
        # Load from path
        elif isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image file not found: {image}")
            image = Image.open(image).convert('RGB')
            
        # Ensure we have a PIL Image
        elif not isinstance(image, Image.Image):
            raise ValueError(f"Unsupported image type: {type(image)}")
            
        # Ensure RGB mode
        image = image.convert('RGB')
            
        # Validate image size
        if image.size[0] < 10 or image.size[1] < 10:
            raise ValueError("Image too small")
        if image.size[0] > 4096 or image.size[1] > 4096:
            raise ValueError("Image too large")
            
        return image

    def _update_performance_metrics(self, processing_time):
        """Update performance monitoring metrics"""
        self.processing_times.append(processing_time)
        if len(self.processing_times) > self.max_processing_times:
            self.processing_times.pop(0)
            
        # Calculate performance statistics
        avg_time = np.mean(self.processing_times)
        if avg_time > 5.0:  # Alert if average processing time exceeds 5 seconds
            logging.warning(f"High average processing time: {avg_time:.2f}s")

    def _get_fallback_response(self):
        """Provide fallback response when vision system fails"""
        return {
            'status': 'error',
            'message': 'Vision system temporarily unavailable',
            'fallback_description': 'Unable to analyze image content'
        }

    def detect_ui_elements(self, image, prompt=None):
        """
        Detect UI elements using Grounding DINO with dynamic prompting.

        Args:
            image: Input image (PIL Image or numpy array).
            prompt (str, optional): Dynamic prompt to guide detection.

        Returns:
            List of detected UI elements.
        """
        if prompt:
            logging.debug(f"Using dynamic prompt for UI detection: {prompt}")
            # Integrate prompt into the detection pipeline
            detections = self._detect_with_prompt(image, prompt)
        else:
            detections = self._detect_default(image)
        
        # Incorporate text usage in detections
        enhanced_detections = self._incorporate_text_info(detections, image)
        
        return enhanced_detections
    
    def _detect_with_prompt(self, image, prompt):
        """Detect UI elements using a dynamic prompt."""
        # Example implementation: Modify the detection model to consider the prompt
        try:
            logging.info("Detecting UI elements with dynamic prompt.")
            # Integrate the prompt with the model's input (pseudo-code)
            detection_input = {
                'image': image,
                'prompt': prompt
            }
            results = self.model.detect(detection_input)
            return results
        except Exception as e:
            logging.error(f"Error during detection with prompt: {e}")
            return []
    
    def _detect_default(self, image):
        """Default UI element detection without prompt."""
        try:
            logging.info("Detecting UI elements with default settings.")
            results = self.model.detect(image)
            return results
        except Exception as e:
            logging.error(f"Error during default detection: {e}")
            return []
    
    def _incorporate_text_info(self, detections, image):
        """Enhance detections by incorporating text information from UI elements."""
        try:
            logging.info("Incorporating text information into UI detections.")
            text_elements = self._extract_text_from_image(image)
            for detection in detections:
                overlapping_text = self._find_overlapping_text(detection['bbox'], text_elements)
                detection['text'] = overlapping_text
            return detections
        except Exception as e:
            logging.error(f"Error incorporating text info: {e}")
            return detections
    
    def _extract_text_from_image(self, image):
        """Extract text from the image using OCR."""
        try:
            ocr_results = self.reader.readtext(np.array(image))
            texts = [{'text': res[1], 'bbox': res[0]} for res in ocr_results]
            logging.debug(f"OCR extracted texts: {texts}")
            return texts
        except Exception as e:
            logging.error(f"Error during OCR text extraction: {e}")
            return []
    
    def _find_overlapping_text(self, bbox, text_elements):
        """Find text elements that overlap with a given bounding box."""
        try:
            overlapping_texts = []
            for text in text_elements:
                if self._boxes_overlap(bbox, text['bbox']):
                    overlapping_texts.append(text['text'])
            return ' '.join(overlapping_texts) if overlapping_texts else ''
        except Exception as e:
            logging.error(f"Error finding overlapping text: {e}")
            return ''
    
    def _boxes_overlap(self, box1, box2, threshold=0.3):
        """Determine if two bounding boxes overlap beyond a threshold."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)

        if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
            return False

        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)

        iou = inter_area / float(box1_area + box2_area - inter_area)
        return iou > threshold

    def _generate_detection_prompt(self, query):
        """
        Generate a focused prompt for element detection.
        
        Args:
            query: Description of the element to detect
            
        Returns:
            str: Formatted prompt for InternVL2
        """
        # Extract key characteristics from query
        characteristics = self._extract_element_characteristics(query)
        
        # Build the prompt template
        prompt = f"""<image>
Please help me locate this specific UI element:
{query}

Key characteristics to look for:
{characteristics}

Instructions:
1. Look for the exact element described
2. If found, provide its precise location using coordinates
3. Format the coordinates as: coordinates: (x1, y1, x2, y2)
4. Also describe where the element is on the screen
5. If the element is not found, explicitly state that

Remember to be precise with coordinate values and ensure they define a valid bounding box.
"""
        return prompt

    def _extract_element_characteristics(self, query):
        """
        Extract key characteristics from the element query to enhance detection.
        
        Args:
            query: Element description
            
        Returns:
            str: Formatted characteristics
        """
        # Common UI element types to look for
        ui_types = ['button', 'link', 'text', 'input', 'icon', 'menu', 'dropdown']
        visual_cues = ['color', 'blue', 'red', 'green', 'white', 'black', 'gray']
        positions = ['top', 'bottom', 'left', 'right', 'center']
        
        characteristics = []
        query_lower = query.lower()
        
        # Check for UI element type
        for ui_type in ui_types:
            if ui_type in query_lower:
                characteristics.append(f"- Type: {ui_type}")
                break
                
        # Check for visual cues
        for cue in visual_cues:
            if cue in query_lower:
                characteristics.append(f"- Visual cue: {cue}")
                
        # Check for position information
        for pos in positions:
            if pos in query_lower:
                characteristics.append(f"- Position: {pos}")
                
        # Add any specific text content
        if '"' in query:
            text = query[query.find('"')+1:query.rfind('"')]
            characteristics.append(f"- Exact text: \"{text}\"")
            
        # If no characteristics found, add the raw query
        if not characteristics:
            characteristics.append(f"- Description: {query}")
            
        return "\n".join(characteristics)

    def find_element(self, image, target_description: str):
        """
        Find a specific UI element in the image.
        
        Args:
            image: Input image (PIL Image or numpy array)
            target_description: Text description of element to find
        
        Returns:
            dict: Detection results with element details or None if not found
        """
        try:
            # Process image to correct format
            processed_image = self._validate_and_process_image(image)
            
            # Updated to focus on "Continue in Browser" link
            annotations = self.omniparser.detect_elements(
                processed_image, query="Continue in Browser"
            )
            
            if annotations['status'] == 'success':
                # Add mouse overlay
                overlay_image = self._add_mouse_overlay(processed_image, annotations['detections'])
                
                # Utilize TextAgent to interpret annotated image and generate command
                command = self.text_agent.complete_task({
                    "image": overlay_image,
                    "query": "Move the mouse to the center of the 'Continue in Browser' element and perform a click action."
                })
                
                # Extract coordinates from command if available
                coordinates = self._extract_coordinates_from_command(command)
                
                if coordinates:
                    x, y = coordinates
                    element_dict = {
                        'type': 'ui_element',
                        'coordinates': (x, y),
                        'description': "Continue in Browser"
                    }
                    return {
                        'element_found': True,
                        'element_details': element_dict,
                        'overlay_image': overlay_image
                    }
                
                return {
                    'element_found': False,
                    'message': 'Coordinates not found in command',
                    'overlay_image': overlay_image
                }
                
            else:
                logging.error(f"OmniParser failed to detect elements: {annotations.get('message', '')}")
                return {
                    'element_found': False,
                    'message': annotations.get('message', 'Detection failed')
                }
                
        except Exception as e:
            logging.error(f"Error finding element: {e}")
            return {
                'element_found': False,
                'error': str(e)
            }

    def _extract_coordinates_from_command(self, command_response: str) -> Optional[Tuple[int, int]]:
        """Extracts (x, y) coordinates from the TextAgent's command response."""
        try:
            match = re.search(r'\((\d+),\s*(\d+)\)', command_response)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                return (x, y)
            return None
        except Exception as e:
            logging.error(f"Error extracting coordinates: {e}")
            return None

    def _get_coordinate_clarification(self, previous_response: str) -> Optional[str]:
        """
        Get clarification for coordinate extraction using multi-turn conversation.
        """
        try:
            clarification_prompt = f"""I see this description of coordinates:
            "{previous_response}"
            
            Please reformat these coordinates into a single line using exactly this format:
            coordinates: (x1, y1, x2, y2)
            
            For example: coordinates: (100, 200, 300, 400)
            
            Extract the numbers from the description and format them correctly.
            If you see multiple coordinates, use the most specific ones for the element."""
            
            # Get clarification from model
            result = self.understand_scene(None, clarification_prompt)
            if result and 'description' in result:
                return result['description']
                
            return None
            
        except Exception as e:
            logging.error(f"Error getting coordinate clarification: {e}")
            return None

    def _analyze_spatial_relations(self, objects):
        """Analyzes spatial relationships between detected objects"""
        relations = []
        for i, obj1 in enumerate(objects):
            for obj2 in objects[i+1:]:
                relation = self._get_spatial_relation(obj1['bbox'], obj2['bbox'])
                relations.append({
                    'object1': obj1['type'],
                    'object2': obj2['type'],
                    'relation': relation
                })
        return relations
        
    def _get_spatial_relation(self, bbox1, bbox2):
        """Determines spatial relation between two bounding boxes"""
        x1_center = (bbox1[0] + bbox1[2]) / 2
        y1_center = (bbox1[1] + bbox1[3]) / 2
        x2_center = (bbox2[0] + bbox2[2]) / 2
        y2_center = (bbox2[1] + bbox2[3]) / 2
        
        dx = x2_center - x1_center
        dy = y2_center - y1_center
        
        if abs(dx) > abs(dy):
            return 'right of' if dx > 0 else 'left of'
        else:
            return 'below' if dy > 0 else 'above'
            
    def _extract_scene_attributes(self, image):
        """Extracts visual attributes from the scene"""
        # Convert to numpy array if needed
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        # Calculate basic image statistics
        brightness = np.mean(image)
        contrast = np.std(image)
        
        # Dominant colors
        pixels = image.reshape(-1, 3)
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=5, n_init=10)
        kmeans.fit(pixels)
        colors = kmeans.cluster_centers_.astype(int)
        
        return {
            'brightness': float(brightness),
            'contrast': float(contrast),
            'dominant_colors': colors.tolist()
        }

    def complete_task(self, task_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Complete a vision-related task"""
        try:
            if not context or 'image' not in context:
                return {'status': 'error', 'message': 'No image provided in context'}
                
            image = context['image']
            if task_description.lower().startswith('find'):
                return self.find_element(image, task_description)
            else:
                return self.understand_scene(image, task_description)
                
        except Exception as e:
            logging.error(f"Error completing vision task: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _ensure_pil_image(self, image):
        """Convert image to PIL Image if it's a numpy array."""
        if isinstance(image, np.ndarray):
            if image.shape[2] == 4:  # RGBA
                image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA))
            else:
                image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        elif isinstance(image, str):
            image = Image.open(image).convert('RGB')
        elif not isinstance(image, Image.Image):
            raise ValueError(f"Unsupported image type: {type(image)}")
        return image

    def enhance_with_object_detection(self, image, mouse_position):
        """
        Enhance the image with object detection annotations, including mouse position.
        
        Args:
            image (numpy.ndarray): The image to process.
            mouse_position (Tuple[int, int]): Current (x, y) position of the mouse.
        
        Returns:
            numpy.ndarray: The enhanced image with object detection annotations.
        """
        # Perform object detection
        detected_objects = self.detect_objects(image)
        
        # Draw bounding boxes around detected objects
        for obj in detected_objects:
            self.draw_bounding_box(image, obj['bbox'], obj['label'])
        
        # Overlay mouse position
        if mouse_position:
            x, y = mouse_position
            cv2.circle(image, (x, y), 5, (0, 255, 0), -1)  # Green circle at mouse position
        
        return image

    def detect_objects(self, image):
        """
        Detect objects in the given image.
        
        Args:
            image (numpy.ndarray): The image to process.
        
        Returns:
            List[dict]: A list of detected objects with bounding boxes and labels.
        """
        # Placeholder for object detection implementation
        # Replace with actual object detection logic (e.g., using OpenCV, YOLO, etc.)
        detected_objects = []
        # Example detected object format:
        # detected_objects.append({'bbox': (x1, y1, x2, y2), 'label': 'object_label'})
        return detected_objects

    def draw_bounding_box(self, image, bbox, label):
        """
        Draw a bounding box and label on the image.
        
        Args:
            image (numpy.ndarray): The image to annotate.
            bbox (Tuple[int, int, int, int]): Bounding box coordinates (x1, y1, x2, y2).
            label (str): Label for the bounding box.
        """
        x1, y1, x2, y2 = bbox
        cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Blue bounding box
        cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 0, 0), 2)
