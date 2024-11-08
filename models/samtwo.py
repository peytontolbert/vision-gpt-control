"""
SAM2-based vision model for UI element detection and segmentation
"""
import torch
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import supervision as sv
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from sam2.sam2.build_sam import build_sam2
from sam2.sam2.sam2_image_predictor import SAM2ImagePredictor
import traceback
import cv2

@dataclass
class SAM2Config:
    """Configuration for SAM2 model"""
    model_name: str = "facebook/sam2-hiera-large"
    device: str = "cuda:0" if torch.cuda.is_available() else "cpu"
    checkpoint: str = "weights/sam2.1_hiera_large.pt"
    model_cfg: str = "sam2/sam2/configs/sam2.1/sam2.1_hiera_l.yaml"

class SAM2:
    def __init__(self, config: Optional[SAM2Config] = None):
        """
        Initialize SAM2 model
        
        Args:
            config: Optional configuration for SAM2
        """
        #self.config = config or SAM2Config()
        self.logger = logging.getLogger(__name__)
        
        try:
            self.predictor = SAM2ImagePredictor(build_sam2(SAM2Config.model_cfg, SAM2Config.checkpoint))
            
            self.logger.info("SAM2 model initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing SAM2: {e}")
            raise RuntimeError(f"SAM2 initialization failed: {str(e)}")

    async def detect_elements(self, image, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect and segment elements in the image
        """
        try:
            # Validate and process image
            image = self._validate_image(image)
            image_np = np.array(image)
            
            # Log image info
            self.logger.info(f"Input image shape: {image_np.shape}")
            
            # Set image in predictor
            self.predictor.set_image(image_np)
            
            # Get masks using SAM2
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                self.logger.info("Running prediction...")
                masks, scores, logits = self.predictor.predict(query)
                
                # Ensure masks are in correct format
                if isinstance(masks, torch.Tensor):
                    masks = masks.cpu().numpy()
                
                self.logger.info(f"Prediction complete:")
                self.logger.info(f"Masks shape: {masks.shape}")
                self.logger.info(f"Scores shape: {scores.shape}")
                self.logger.info(f"Score range: {scores.min():.3f} to {scores.max():.3f}")

            # Sort masks by score
            sorted_idx = np.argsort(scores)[::-1]  # Descending order
            masks = masks[sorted_idx]
            scores = scores[sorted_idx]

            # Format detections
            detections = []
            for i, (mask, score) in enumerate(zip(masks, scores)):
                # Get bounding box from mask
                y_indices, x_indices = np.where(mask)
                if len(y_indices) > 0 and len(x_indices) > 0:
                    x1, x2 = np.min(x_indices), np.max(x_indices)
                    y1, y2 = np.min(y_indices), np.max(y_indices)
                    
                    detection = {
                        'type': 'ui_element',
                        'coordinates': ((x1 + x2) / 2, (y1 + y2) / 2),
                        'bbox': (float(x1), float(y1), float(x2), float(y2)),
                        'mask': mask.tolist(),
                        'confidence': float(score),
                        'width': float(x2 - x1),
                        'height': float(y2 - y1),
                        'area': float((x2 - x1) * (y2 - y1)),
                        'aspect_ratio': float((x2 - x1) / (y2 - y1)) if (y2 - y1) > 0 else 0
                    }
                    detections.append(detection)

            self.logger.info(f"Found {len(detections)} valid detections")

            # Create annotated image
            boxes = np.array([d['bbox'] for d in detections]) if detections else np.empty((0, 4))
            annotated_frame = self._create_annotated_image(image_np, boxes, masks)

            return {
                'status': 'success',
                'detections': detections,
                'annotated_image': Image.fromarray(annotated_frame),
                'raw_masks': masks.tolist()
            }

        except Exception as e:
            self.logger.error(f"Error in element detection: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': str(e)
            }

    def _validate_image(self, image) -> Image.Image:
        """Validate and convert image to PIL Image"""
        if isinstance(image, np.ndarray):
            return Image.fromarray(image)
        elif isinstance(image, str):
            return Image.open(image)
        elif isinstance(image, Image.Image):
            return image
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def _create_annotated_image(self, image: np.ndarray, boxes: np.ndarray, masks: np.ndarray) -> np.ndarray:
        """Create annotated image with boxes and masks using show_masks and show_box"""
        try:
            # Create figure with proper size matching input image
            dpi = 100
            height, width = image.shape[:2]
            figsize = (width/dpi, height/dpi)
            
            fig = plt.figure(figsize=figsize, dpi=dpi)
            ax = plt.gca()
            
            # Display base image
            ax.imshow(image)
            
            # Handle empty detections case
            if boxes.shape[0] == 0 or len(masks) == 0:
                self.logger.warning("No detections to annotate")
                plt.close()
                return image
            
            # Convert masks to correct format if needed
            if isinstance(masks, list):
                masks = np.array(masks)
                
            # Show each mask with random colors and borders
            for i, (mask, box) in enumerate(zip(masks, boxes)):
                # Show mask with random color
                self.show_mask(mask, ax, random_color=True, borders=True)
                
                # Show bounding box
                self.show_box(box, ax)
            
            # Remove axes and padding
            plt.axis('off')
            plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
            plt.margins(0, 0)
            
            # Convert figure to numpy array
            fig.canvas.draw()
            annotated_frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            annotated_frame = annotated_frame.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            
            plt.close()
            
            return annotated_frame

        except Exception as e:
            self.logger.error(f"Error creating annotated image: {e}")
            self.logger.error(f"Masks shape: {masks.shape}, Boxes shape: {boxes.shape}")
            self.logger.error(traceback.format_exc())
            return image.copy()

    def segment_element(self, image: Image.Image, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mask for specific element given a prompt
        
        Args:
            image: Input image
            prompt: Prompt dictionary (can contain box, points, or text)
            
        Returns:
            Dict containing segmentation mask and visualization
        """
        self.logger.debug(f"Received segmentation prompt: {prompt}")
        try:
            image_np = np.array(image)
            self.predictor.set_image(image_np)
            
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                masks, scores, _ = self.predictor.predict(prompt)
            
            # Take highest scoring mask
            best_idx = scores.argmax()
            mask = masks[best_idx]
            
            # Get bounding box from mask
            y_indices, x_indices = np.where(mask)
            bbox = [
                float(np.min(x_indices)),
                float(np.min(y_indices)),
                float(np.max(x_indices)),
                float(np.max(y_indices))
            ]
            
            # Create visualization
            annotated = self._create_annotated_image(
                image_np,
                np.array([bbox]),
                np.array([mask])
            )
            
            return {
                'status': 'success',
                'mask': mask.tolist(),
                'confidence': float(scores[best_idx]),
                'bbox': bbox,
                'visualization': Image.fromarray(annotated)
            }
            
        except Exception as e:
            self.logger.error(f"Error in element segmentation: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
            
    def show_mask(self, mask, ax, random_color=False, borders = True):
        if random_color:
            color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
        else:
            color = np.array([30/255, 144/255, 255/255, 0.6])
        h, w = mask.shape[-2:]
        mask = mask.astype(np.uint8)
        mask_image =  mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
        if borders:
            import cv2
            contours, _ = cv2.findContours(mask,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
            # Try to smooth contours
            contours = [cv2.approxPolyDP(contour, epsilon=0.01, closed=True) for contour in contours]
            mask_image = cv2.drawContours(mask_image, contours, -1, (1, 1, 1, 0.5), thickness=2) 
        ax.imshow(mask_image)

    def show_points(self, coords, labels, ax, marker_size=375):
        pos_points = coords[labels==1]
        neg_points = coords[labels==0]
        ax.scatter(pos_points[:, 0], pos_points[:, 1], color='green', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)
        ax.scatter(neg_points[:, 0], neg_points[:, 1], color='red', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)   

    def show_box(self, box, ax):
        x0, y0 = box[0], box[1]
        w, h = box[2] - box[0], box[3] - box[1]
        ax.add_patch(plt.Rectangle((x0, y0), w, h, edgecolor='green', facecolor=(0, 0, 0, 0), lw=2))    

    def show_masks(self, image, masks, scores, point_coords=None, box_coords=None, input_labels=None, borders=True):
        for i, (mask, score) in enumerate(zip(masks, scores)):
            plt.figure(figsize=(10, 10))
            plt.imshow(image)
            self.show_mask(mask, plt.gca(), borders=borders)
            if point_coords is not None:
                assert input_labels is not None
                self.show_points(point_coords, input_labels, plt.gca())
            if box_coords is not None:
                # boxes
                self.show_box(box_coords, plt.gca())
            if len(scores) > 1:
                plt.title(f"Mask {i+1}, Score: {score:.3f}", fontsize=18)
            plt.axis('off')
            plt.show()

    def show_anns(self, anns, borders=True):
        if len(anns) == 0:
            return
        sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
        ax = plt.gca()
        ax.set_autoscale_on(False)

        img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
        img[:, :, 3] = 0
        for ann in sorted_anns:
            m = ann['segmentation']
            color_mask = np.concatenate([np.random.random(3), [0.5]])
            img[m] = color_mask 
            if borders:
                import cv2
                contours, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
                # Try to smooth contours
                contours = [cv2.approxPolyDP(contour, epsilon=0.01, closed=True) for contour in contours]
                cv2.drawContours(img, contours, -1, (0, 0, 1, 0.4), thickness=1) 

        ax.imshow(img)