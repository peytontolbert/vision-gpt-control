"""
This is the text Agent that completes text tasks for the input
"""
from agents.base import BaseAgent
import base64
from PIL import Image
import io
import logging

class TextAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

    def encode_image(self, image_path):
        """Encode image file to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def encode_pil_image(self, pil_image):
        """Encode PIL Image to base64 string"""
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def complete_task(self, input):
        """Complete text task with optional image input and enforce command format."""
        self.logger.debug(f"generate_command called with input_data: {input} (type: {type(input)})")
        # Check if input contains an image tag
        if isinstance(input, dict) and "query" in input and "image" in input:
            query = input["query"]
            image = self.encode_image(input["image"])

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image}"
                            }
                        }
                    ]
                }
            ]
        elif isinstance(input, str) and "<image>" in input and "</image>" in input:
            # Extract base64 string between image tags
            start_idx = input.find("<image>") + 7
            end_idx = input.find("</image>")
            base64_str = input[start_idx:end_idx].strip()
            
            # Create message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": input[:start_idx-7]},  # Text before image
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_str}"
                            }
                        },
                        {"type": "text", "text": input[end_idx+8:]}  # Text after image
                    ]
                }
            ]
        else:
            # Regular text-only message
            messages = [{"role": "user", "content": input}]

        # Append instruction to enforce command format
        instruction = "Please provide your response in the following format exactly: 'move to (x, y)' or 'move to (x, y) and click'. Do not include any additional text."
        messages[0]["content"].append({"type": "text", "text": instruction})

        # Make API call with proper model that supports vision
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Use vision-capable model
            messages=messages,
            max_tokens=1000,
        )
        
        return response.choices[0].message.content

    def generate_command(self, input_data):
        """
        Generate a mouse command based on the provided input data.

        Args:
            input_data (dict): Contains the query for command generation.

        Returns:
            str: Generated mouse command.
        """
        self.logger.debug(f"TextAgent.generate_command called with input_data: {input_data} (type: {type(input_data)})")
        # Check if input_data contains necessary fields
        if "query" not in input_data:
            self.logger.error("Input data missing 'query' field.")
            raise ValueError("Input data must contain a 'query' field.")

        query = input_data["query"]

        # Prepare messages for the language model
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # Make API call with proper model that supports vision
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure the model supports the required capabilities
            messages=messages,
            max_tokens=150,
        )

        # Extract and return the generated command
        generated_command = response.choices[0].message.content.strip()
        self.logger.debug(f"TextAgent.generate_command returning: {generated_command}")
        return generated_command

