"""
This is the text Agent that completes text tasks for the input
"""
from agents.base import BaseAgent
import base64
from PIL import Image
import io
import logging
import cv2
import tempfile
import os
import time
import numpy as np  # Added to handle numpy arrays
import re
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
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
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
        """Complete text task with optional image input and enforce command format."""
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

    def generate_command(self, input_data):
        """
        Generate a machine-readable mouse command based on input data within a custom coordinate system.
        Ensures the command follows the expected format and stays within custom viewport bounds.
        
        Args:
            input_data (dict): Contains 'query' and 'image' keys.
        
        Returns:
            str: The generated command in format 'move to (x, y)' or 'move to (x, y) and click'.
        """
        query = (
            f"Based on the given mouse position {input_data.get('mouse_position')}, "
            "generate a machine-readable command to move the mouse to the specified position and perform an action. "
            "and follows one of the following exact formats: 'move to (x, y)' or 'move to (x, y) and click'. No additional text should be included."
        )
        try:
            command = self.complete_task({
                "image": input_data.get("image", ""),
                "query": query
            })
            print(f"Generated command: {command}")
            # Validate that the command coordinates are within custom bounds
            match = re.fullmatch(r"move to \((\d{1,4}),\s*(\d{1,4})\)( and click)?", command.strip(), re.IGNORECASE)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                return command.strip()
            else:
                self.logger.error(f"Command does not match expected format: {command}")
                # Handle the error using ErrorController
                self.error_controller.handle_error(
                    error=ValueError("Command format mismatch"),
                    context="generate_command",
                    retry_callback=lambda: self.generate_command(input_data)  # Retry the command generation
                )
                return ""
        except Exception as e:
            self.logger.error(f"Error generating command: {e}")
            # Handle the error using ErrorController
            self.error_controller.handle_error(
                error=e,
                context="generate_command",
                retry_callback=lambda: self.generate_command(input_data)  # Retry the command generation
            )
            return ""

    def decide_next_action(self, enhanced_image, mouse_position, prompt: str) -> str:
        """
        Decide the next mouse action based on the enhanced prompt.
        Supports multi-step interactions by maintaining context.
        
        Args:
            enhanced_image (numpy.ndarray): The enhanced image from VisionAgent.
            mouse_position (tuple): Current mouse position.
            prompt (str): The enhanced prompt from ManagerAgent.
        
        Returns:
            str: The next action command.
        """
        input_data = {
            "query": self._compose_prompt(prompt, mouse_position),
            "image": enhanced_image
        }
        print(f"Input data: {input_data}")
        command = self.generate_command(input_data)
        print(f"Generated command: {command}")
        if not command:
            self.logger.error("Failed to generate a valid command.")
            # Handle the error using ErrorController
            self.error_controller.handle_error(
                error=RuntimeError("Failed to generate a valid command"),
                context="decide_next_action",
                retry_callback=lambda: self.decide_next_action(enhanced_image, mouse_position, prompt)  # Retry deciding the next action
            )
        return command

    def review_result(self, screen_image, mouse_position):
        """
        Review the current screen and mouse position to determine if the task is complete.
        
        Args:
            screen_image (numpy.ndarray): The current screen image.
            mouse_position (tuple): The current mouse position (x, y).
        
        Returns:
            str: The review result or command to continue.
        """
        try:
            # Save the screen image temporarily
            temp_path = self._save_image(screen_image, "review_result")
            input_data = {
                "image": temp_path,
                "query": (
                    f"Given the current mouse position at {mouse_position}, "
                    "review the screen image to determine if the task is complete."
                )
            }
            # Get response from TextAgent
            response = self.complete_task(input_data)
            return response
        except Exception as e:
            self.logger.error(f"Error in review_result: {e}")
            return None

    def _save_image(self, image, label):
        """
        Save the image to a temporary file and return the path.
        
        Args:
            image (numpy.ndarray): The image to save.
            label (str): A label for the image.
        
        Returns:
            str: The file path of the saved image.
        """
        try:
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            filename = f"{label}_{timestamp}.png"
            file_path = os.path.join(temp_dir, filename)
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            pil_image.save(file_path)
            self.logger.debug(f"Saved image {label} to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"Error saving image {label}: {e}")
            return None

    def _compose_prompt(self, prompt, mouse_position):
        """
        Compose a prompt by incorporating the task prompt and mouse position.

        Args:
            prompt (str): The task description.
            mouse_position (tuple): The current mouse position (x, y).

        Returns:
            str: The composed prompt.
        """
        return f"{prompt}\nCurrent mouse position: {mouse_position}."

    def decide_next_action_from_history(self, enhanced_image, history) -> str:
        """
        Decide the next mouse action based on previous attempts history.
        
        Args:
            enhanced_image (str): Path to the enhanced image with failed attempts.
            history (list): List of dictionaries containing previous attempts and task.
        
        Returns:
            str: The next action command.
        """
        # Extract the original task from history
        task = next((entry['task'] for entry in history if 'task' in entry), '')
        
        # Create a prompt that includes previous attempt information
        failed_positions = [
            pos for entry in history 
            for key, pos in entry.items() 
            if '_mouse_pos' in key
        ]
        
        prompt = (
            f"Task: {task}\n"
            f"Previous failed attempts at positions: {failed_positions}\n"
            "Based on the previous failed attempts marked with X's on the image, "
            "suggest a new position to click that hasn't been tried before. "
            "Stay within the custom coordinate system (width: 1000, height: 600)."
        )
        
        input_data = {
            "query": prompt,
            "image": enhanced_image
        }
        
        command = self.generate_command(input_data)
        if not command:
            self.logger.error("Failed to generate a valid command from history.")
            self.error_controller.handle_error(
                error=RuntimeError("Failed to generate a valid command from history"),
                context="decide_next_action_from_history",
                retry_callback=lambda: self.decide_next_action_from_history(enhanced_image, history)
            )
        return command

