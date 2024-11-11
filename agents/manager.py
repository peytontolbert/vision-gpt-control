from agents.base import BaseAgent
import logging
from agents.text import TextAgent
from controllers.error_controller import ErrorController  # Import ErrorController

class ManagerAgent(BaseAgent):
    def __init__(self, text_agent: TextAgent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.text_agent = text_agent
        self.error_controller = ErrorController()  # Initialize ErrorController

    def enhance_prompt(self, task: str, metadata: dict) -> str:
        """
        Incorporate text and metadata into an enhanced prompt for the TextAgent.
        Specifies whether to use the mouse or keyboard based on the task.
        
        Args:
            task (str): The current task description.
            metadata (dict): Additional metadata relevant to the task.
        
        Returns:
            str: The enhanced prompt.
        """
        self.logger.debug(f"Enhancing prompt with task: {task} and metadata: {metadata}")
        prompt = f"Task: {task}\n"
        for key, value in metadata.items():
            if task == "enter username" and key == "DISCORD_USER":
                prompt += f"{key.capitalize()}: {value}\n"  # Insert username
            elif task == "enter password" and key == "DISCORD_PASS":
                prompt += f"{key.capitalize()}: {value}\n"  # Insert password
            else:
                prompt += f"{key.capitalize()}: {value}\n"
        # Specify input method based on task
        if task in ["enter username", "enter password"]:
            prompt += "Use the keyboard to input the provided credentials.\n"
        elif task == "submit login":
            prompt += "Use the mouse to click the login button.\n"
        elif task == "click username field":
            prompt += "Use the mouse to click on the username field to activate it.\n"
        elif task == "click password field":
            prompt += "Use the mouse to click on the password field to activate it.\n"
        prompt += "Please provide the next action based on the above information."
        
        try:
            return prompt
        except Exception as e:
            self.logger.error(f"Error enhancing prompt: {e}")
            # Handle the error using ErrorController
            self.error_controller.handle_error(
                error=e,
                context="enhance_prompt",
                retry_callback=lambda: self.enhance_prompt(task, metadata)  # Retry enhancing the prompt
            )
            return ""

    # Optionally, add methods to control flow between keyboard and mouse if needed
    # For example:
    def should_use_keyboard(self, task: str) -> bool:
        """
        Determines whether to use the keyboard based on the task.
        
        Args:
            task (str): The current task description.
        
        Returns:
            bool: True if keyboard should be used, False otherwise.
        """
        return task in ["enter username", "enter password"]

    def should_use_mouse(self, task: str) -> bool:
        """
        Determines whether to use the mouse based on the task.
        
        Args:
            task (str): The current task description.
        
        Returns:
            bool: True if mouse should be used, False otherwise.
        """
        return task == "submit login"

    def verify_action(self, overlay_image, expected_prompt) -> bool:
        """
        Verify if the intended action was successfully completed by analyzing the overlay image.

        Args:
            overlay_image (str): Path to the overlay image after the action.
            expected_prompt (str): Description of the expected state after the action.

        Returns:
            bool: True if the action was successful, False otherwise.
        """
        prompt = f"Based on the provided overlay image, determine if the mouse is in the correct position.\nExpected state: {expected_prompt}. Reply with yes or no"
        response = self.text_agent.complete_task({
            "query": prompt,
            "image": overlay_image
        })
        print(f"Verification response: {response}")
        return "yes" in response.strip().lower()
        