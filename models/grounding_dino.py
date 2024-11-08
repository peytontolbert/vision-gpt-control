import torch
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection 
import numpy as np
from PIL import Image
from typing import List, Tuple

class GroundingDINO:
    def __init__(self):
        """Initialize GroundingDINO model.
        
        Args:
            model_config_path: Path to model config file
            model_checkpoint_path: Path to model weights
        """
        model_id = "IDEA-Research/grounding-dino-base"
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        
        # Load config
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(self.device)

    def predict_with_caption(
        self,
        image: np.ndarray,
        caption: str,
        box_threshold: float = 0.35,
        text_threshold: float = 0.25
    ) -> Tuple[List[List[float]], List[float]]:
        """Predict bounding boxes for the given caption in the image.
        
        Args:
            image: numpy array of shape (H, W, C)
            caption: Text description to ground in the image
            box_threshold: Confidence threshold for bounding boxes
            text_threshold: Confidence threshold for text

        Returns:
            boxes: List of bounding boxes [x1, y1, x2, y2]
            scores: Confidence scores for each box
        """
        # Convert numpy array to PIL Image if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        inputs = self.processor(images=image, text=caption, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)

        results = self.processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            box_threshold=0.4,
            text_threshold=0.3,
            target_sizes=[image.size[::-1]]
        )

        return results

