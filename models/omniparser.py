"""
OmniParser agent for UI element detection and OCR
"""
import torch
import numpy as np
from PIL import Image, ImageDraw
import cv2
import logging
import os
import io
import base64
from ultralytics import YOLO
import supervision
import easyocr
from typing import Optional, Tuple, List, Dict, Any
import time
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from utils import get_som_labeled_img, check_ocr_box, get_caption_model_processor, get_yolo_model
WEIGHTS_PATH = "D:/bob-agi/OmniParser/icon_detect/best.pt"
BLIP_MODEL_PATH = "D:/bob-agi/OmniParser/icon_caption_blip2"
BOX_THRESHOLD = 0.02
DRAW_BBOX_CONFIG = {
    'text_scale': 0.8,
    'text_thickness': 2,
    'text_padding': 3,
    'thickness': 3,
}

class OmniParser:
    def __init__(self):
        self.model = self._load_model()
        if torch.cuda.is_available():
            self.model.to('cuda')
            
        # Initialize OCR
        self.reader = easyocr.Reader(['en'])
        
        # Initialize BLIP
        self.caption_processor = self._load_caption_model()


    def _load_model(self):
        """Load the OmniParser YOLO model"""
        try:
            model = YOLO(WEIGHTS_PATH)
            logging.info("OmniParser model loaded successfully")
            return model
        except Exception as e:
            logging.error(f"Failed to load OmniParser model: {e}")
            raise RuntimeError(f"OmniParser model initialization failed: {str(e)}")

    def _load_caption_model(self) -> Dict[str, Any]:
        """Load the BLIP captioning model"""
        try:
            caption_model_processor = get_caption_model_processor(
                model_name="blip2",
                model_name_or_path=BLIP_MODEL_PATH,
                device='cuda:0'
            )
            model = Blip2ForConditionalGeneration.from_pretrained(BLIP_MODEL_PATH)
            if torch.cuda.is_available():
                model.to('cuda')
            return {'processor': caption_model_processor, 'model': model}
        except Exception as e:
            logging.error(f"Failed to load BLIP model: {e}")
            raise RuntimeError(f"BLIP model initialization failed: {str(e)}")

    def detect_elements(self, image, query=None):
        """
        Detect elements in the image based on the query.
        Returns a dictionary with status and detections.
        """
        # Implement the detection logic
        # Example return structure:
        return {
            'status': 'success',
            'detections': [
                {
                    'description': 'Join Button',
                    'bbox': (100, 150, 200, 250)
                },
                # ... more detections ...
            ],
            'labeled_image': image  # or the path to the labeled image
        }

    #   def check_ocr_box(self, image_path, display_img=False, output_bb_format='xyxy'):
        # Perform OCR on image and return text and bounding boxes
    #    try:
    #        result = self.reader.readtext(image_path)
            
    #        text = []
    #        boxes = []
            
    #        for detection in result:
    #            bbox = detection[0]  # Get bounding box coordinates
    #            text_content = detection[1]  # Get text content

    #            # Convert to xyxy format if needed
    #            if output_bb_format == 'xyxy':
    #                x1 = min(bbox[0][0], bbox[2][0])
    #                y1 = min(bbox[0][1], bbox[2][1])
    #                x2 = max(bbox[0][0], bbox[2][0])
    #                y2 = max(bbox[0][1], bbox[2][1])
    #                boxes.append([x1, y1, x2, y2])
    #            else:
    #                 boxes.append(bbox)
                        
    #             text.append(text_content)
                        
    #         return (text, boxes), False
                        
    #     except Exception as e:
    #        logging.error(f"Error in OCR processing: {e}")
    #        return ([], []), False

    def get_labeled_img(self, image_path, model, box_threshold, ocr_bbox=None, 
                       draw_bbox_config=None, ocr_text=None):
        # Run element detection and label image
        try:
            # Run YOLO detection
            results = model(image_path)[0]
            
            # Process results
            boxes = results.boxes.cpu().numpy()
            class_ids = boxes.cls
            conf = boxes.conf
            xyxy = boxes.xyxy
            
            # Load original image for cropping
            original_image = Image.open(image_path)
            
            # Convert to list of dictionaries
            parsed_content = []
            for i in range(len(class_ids)):
                if conf[i] > box_threshold:
                    element = {
                        'label': results.names[int(class_ids[i])],
                        'bbox': xyxy[i].tolist(),
                        'confidence': float(conf[i])
                    }
                    
                    # Add OCR text if available
                    if ocr_text and ocr_bbox:
                        element['text'] = self._find_overlapping_text(
                            element['bbox'], 
                            ocr_bbox, 
                            ocr_text
                        )
                    
                    # Add BLIP caption
                    if self.caption_processor:
                        crop = self._crop_bbox(original_image, element['bbox'])
                        caption = self._generate_caption(crop)
                        element['caption'] = caption
                        
                    parsed_content.append(element)
            
            # Create labeled image
            image = Image.open(image_path)
            labeled_img = self._draw_detections(image, parsed_content, draw_bbox_config)
            
            return labeled_img, xyxy, parsed_content
            
        except Exception as e:
            logging.error(f"Error in element detection: {e}")
            raise

    def _find_overlapping_text(self, element_bbox, ocr_boxes, ocr_text):
        """Find OCR text that overlaps with detected element"""
        def calculate_iou(box1, box2):
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            
            if x2 < x1 or y2 < y1:
                return 0.0
                
            intersection = (x2 - x1) * (y2 - y1)
            box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
            box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
            
            return intersection / (box1_area + box2_area - intersection)

        overlapping_text = []
        for bbox, text in zip(ocr_boxes, ocr_text):
            if calculate_iou(element_bbox, bbox) > 0.5:
                overlapping_text.append(text)
                
        return ' '.join(overlapping_text)

    def _draw_detections(self, image, detections, config):
        """Draw bounding boxes and labels on image"""
        draw = ImageDraw.Draw(image)
        
        for det in detections:
            bbox = det['bbox']
            label = det['label']
            conf = det['confidence']
            text = det.get('text', '')
            
            # Draw box
            draw.rectangle(bbox, outline='red', width=config['thickness'])
            
            # Draw label
            label_text = f"{label} ({conf:.2f})"
            if text:
                label_text += f": {text}"
                
            draw.text((bbox[0], bbox[1] - 20), label_text, fill='red')
            
        # Convert to bytes instead of base64 string
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return buffered.getvalue()  # Return bytes directly instead of base64 encoding

    def _format_detections(self, parsed_content):
        """Convert parsed content to standard detection format"""
        detections = []
        for element in parsed_content:
            x1, y1, x2, y2 = element['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            detection = {
                'type': element['label'],
                'coordinates': (center_x, center_y),
                'bbox': (x1, y1, x2, y2),
                'description': element.get('text', ''),
                'caption': element.get('caption', ''),
                'width': x2 - x1,
                'height': y2 - y1,
                'confidence': element.get('confidence', 0.0)
            }
            detections.append(detection)
            
        return detections

    def _save_temp_image(self, image: Image.Image) -> str:
        """Save PIL Image to temporary file and return path"""
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"temp_image_{time.time()}.jpg")
        image.save(temp_path)
        return temp_path

    def _generate_caption(self, image: Image.Image) -> str:
        """Generate caption for cropped image using BLIP"""
        try:
            # Debug: Check the type of caption_processor['processor']
            if not callable(self.caption_processor['processor']):
                logging.error("Processor is not callable. Check initialization.")
                return ""
            
            inputs = self.caption_processor['processor'](image, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
            outputs = self.caption_processor['model'].generate(**inputs, max_length=30)
            
            # Ensure that 'decode' is called on the processor, not the dict
            caption = self.caption_processor['processor'].decode(outputs[0], skip_special_tokens=True)
            return caption
        except Exception as e:
            logging.error(f"Error generating caption: {e}")
            return ""

    def _crop_bbox(self, image, bbox):
        """Crop image according to bounding box"""
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        return image.crop((x1, y1, x2, y2))

    def _load_som_model(self):
        """Load the OmniParser SOM model"""
        try:
            model = YOLO(WEIGHTS_PATH)
            logging.info("OmniParser model loaded successfully")
            return model
        except Exception as e:
            logging.error(f"Failed to load OmniParser model: {e}")
            raise RuntimeError(f"OmniParser model initialization failed: {str(e)}")
