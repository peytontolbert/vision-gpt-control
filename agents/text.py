"""
This is the text Agent that completes text tasks for the input
"""
from agents.base import BaseAgent
import base64
from PIL import Image
import io
import logging
import numpy as np  # Added to handle numpy arrays
import os
import time
import tempfile
import requests
from controllers.error_controller import ErrorController  # Import ErrorController

class TextAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()  # Initialize a session
        self.error_controller = ErrorController()  # Initialize ErrorController

    def encode_image(self, image):
        """Encode image file or PIL Image to base64 string"""
        try:
            if isinstance(image, Image.Image):
                # Save the PIL Image to a temporary file
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time())
                filename = f"temp_image_{timestamp}.png"
                file_path = os.path.join(temp_dir, filename)
                image.save(file_path, format='PNG')
                logging.debug(f"Temporary image saved at {file_path}")
            elif isinstance(image, str):
                file_path = image
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Image file not found: {file_path}")
            elif isinstance(image, np.ndarray):
                pil_image = Image.fromarray(image)
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time())
                filename = f"temp_image_{timestamp}.png"
                file_path = os.path.join(temp_dir, filename)
                pil_image.save(file_path, format='PNG')
                logging.debug(f"Temporary image saved at {file_path}")
            else:
                raise TypeError("encode_image expects a file path, PIL.Image, or numpy.ndarray")

            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            # Optionally remove the temporary file if it was created
            if isinstance(image, Image.Image) or isinstance(image, np.ndarray):
                os.remove(file_path)
                logging.debug(f"Temporary image {file_path} removed after encoding.")

            return encoded_string
        except Exception as e:
            self.logger.error(f"Error encoding image: {e}")
            return None

    def complete_task(self, input):
        """Complete text task with optional image input."""
        self.logger.debug(f"complete_task called with input: {input}")
        
        try:
            if isinstance(input, dict) and "query" in input and "image" in input:
                # Encode the image file to base64
                base64_image = self.encode_image(input["image"])
                if not base64_image:
                    raise ValueError("Failed to encode image")

                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": input["query"]},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            else:
                # Regular text-only message
                messages = [{"role": "user", "content": input}]

            # Make API call with stricter instructions
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1000,
                temperature=0  # Set temperature to 0 for deterministic output
            )
            print(f"Response: {response.choices[0].message.content}")
            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error in complete_task: {e}")
            raise

