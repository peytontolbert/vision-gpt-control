from typing import Tuple, Optional
import re
import logging
import time  # Import time for adding delays
from controllers.error_controller import ErrorController
from agents.command_formatter import CommandFormatterAgent
from overlay.overlay import Overlay

class NLPMouseController:
    """
    A controller that translates natural language commands into mouse movements.
    """
    def __init__(self, mouse, screen, text_agent, command_formatter):
        self.mouse = mouse
        self.screen = screen
        self.text_agent = text_agent
        self.command_formatter = command_formatter
        
        # Define movement mappings
        self.distance_mappings = {
            'tiny': 5,
            'very small': 10,
            'small': 20,
            'medium': 50,
            'large': 100,
            'very large': 200,
            'huge': 400
        }
        
        self.direction_mappings = {
            'up': (0, -1),
            'down': (0, 1),
            'left': (-1, 0),
            'right': (1, 0),
            'up-left': (-1, -1),
            'up-right': (1, -1),
            'down-left': (-1, 1),
            'down-right': (1, 1)
        }
        
        # Add relative position mappings
        self.position_mappings = {
            'center': lambda w, h: (w//2, h//2),
            'top': lambda w, h: (w//2, 0),
            'bottom': lambda w, h: (w//2, h),
            'left': lambda w, h: (0, h//2),
            'right': lambda w, h: (w, h//2),
            'top-left': lambda w, h: (0, 0),
            'top-right': lambda w, h: (w, 0),
            'bottom-left': lambda w, h: (0, h),
            'bottom-right': lambda w, h: (w, h)
        }

        self.current_command = None  # Initialize current_command
        self.current_context = None  # Initialize current_context
        self.max_regeneration_attempts = 5  # Increased from 3
        self.regeneration_count = 0  # Counter for regeneration attempts
        self.error_controller = ErrorController(
            max_retries=4, 
            initial_retry_delay=2, 
            backoff_factor=2.0
        )

        self.command_map = {
            'move': self.handle_move,
            'click': self.handle_click,
            'scroll': self.handle_scroll
            # Add more command handlers as needed
        }

        self.overlay = Overlay()  # Initialize Overlay instance

        # Define viewport dimensions
        self.CUSTOM_VIEWPORT_WIDTH, self.CUSTOM_VIEWPORT_HEIGHT = 776, 464  # **Added Line**

        # If CUSTOM_VIEWPORT is necessary, set it based on screen size
        self.CUSTOM_VIEWPORT_WIDTH, self.CUSTOM_VIEWPORT_HEIGHT = self.screen.width, self.screen.height  # **Remove or Adjust if Needed**

    def parse_movement(self, command: str) -> Optional[Tuple[int, int]]:
        """
        Parse a validated machine-readable movement command.
        
        Example:
        - "move to (100, 200)"
        - "move to (100, 200) and click"
        
        Returns:
            Tuple[int, int]: The (x, y) absolute position to move to, or None if invalid
        """
        command = command.lower().strip()
        match = re.search(r"move to \((\d+),\s*(\d+)\)", command)
        if not match:
            logging.error(f"Command does not match expected pattern: {command}")
            return None
        try:
            target_x = int(match.group(1))
            target_y = int(match.group(2))
            
            # Use absolute positions instead of deltas
            return (target_x, target_y)
        except ValueError:
            logging.error(f"Invalid coordinates in command: {command}")
            return None

    def move(self, command: str) -> bool:
        """
        Execute a machine-readable movement command.
        
        Args:
            command: Movement command in the format "move to (x, y)" or "move to (x, y) and click"
            
        Returns:
            bool: True if movement was executed successfully
        """
        # Deprecated method. Use 'execute_command' instead to ensure proper handling.
        logging.warning("Deprecated method 'move' called. Use 'execute_command' instead.")
        return self.execute_command(command)

    def move_to_relative_position(self, position: str) -> bool:
        """Move to a relative screen position."""
        if position in self.position_mappings:
            screen_width = self.screen.width
            screen_height = self.screen.height
            x, y = self.position_mappings[position](screen_width, screen_height)
            return self.mouse.move_to(x, y)
        return False

    def execute_command(self, command: str) -> bool:
        """
        Execute a machine-readable movement command with action verification.
        
        Args:
            command: Movement command in natural language or formatted form
            
        Returns:
            bool: True if movement and action were executed successfully
        """
        logging.debug(f"Executing command: {command}")
        
        retry_attempts = 0
        max_retries = self.max_regeneration_attempts

        while retry_attempts < max_retries:
            # Format the command if it's not already formatted
            if not self.command_formatter.validate_command(command):
                formatted_command = self.command_formatter.format_command(command)
                if not formatted_command:
                    logging.error(f"Failed to format command: {command}")
                    
                    # Attempt to regenerate the command using TextAgent
                    new_command = self._regenerate_command()
                    if new_command and self.command_formatter.validate_command(new_command):
                        logging.info(f"Regenerated command: {new_command}")
                        command = new_command
                        retry_attempts += 1
                        continue
                    else:
                        logging.error("Failed to regenerate a valid command.")
                        return False  # Exit if regeneration fails
                else:
                    logging.debug(f"Formatted command: {formatted_command}")
                    command = formatted_command

            parsed = self.parse_command(command)
            if not parsed:
                logging.error(f"Failed to parse command: {command}")
                return False
                        
            x, y, action = parsed

            logging.debug(f"Parsed command coordinates: ({x}, {y}), Action: {action}")

            # Clamp coordinates
            x = max(0, min(x, self.CUSTOM_VIEWPORT_WIDTH))
            y = max(0, min(y, self.CUSTOM_VIEWPORT_HEIGHT))
            logging.debug(f"Clamped coordinates to viewport bounds: ({x}, {y})")

            # Move the mouse to the target position within viewport
            success = self.mouse.move_to(x, y)
            if not success:
                logging.error(f"Failed to move mouse to ({x}, {y})")
                retry_attempts += 1
                continue  # Retry movement

            # Verify mouse position within viewport
            if not self._verify_location(x, y):
                logging.error(f"Mouse not at the expected position after moving to ({x}, {y})")
                retry_attempts += 1
                continue  # Retry movement

            # Optional: Add a short delay to ensure the UI has time to respond to the mouse movement
            time.sleep(0.5)
                        
            if action:
                logging.debug(f"Executing action: {action}")
                action_success = False
                if action == "click":
                    action_success = self.mouse.click()
                elif action == "double-click":
                    action_success = self.mouse.double_click()
                elif action == "right-click":
                    action_success = self.mouse.right_click()
                else:
                    logging.error(f"Unknown action: {action}")
                    return False
                
                if not action_success:
                    logging.error(f"Failed to execute {action} action at ({x}, {y})")
                    retry_attempts += 1
                    continue  # Retry action

                logging.debug(f"Action '{action}' executed successfully at ({x}, {y})")
                
                # Verify the click action
                if not self._verify_click_success(x, y):
                    logging.error(f"Click action not verified at ({x}, {y})")
                    retry_attempts += 1
                    continue  # Retry action verification

            return True  # Successfully executed command

        logging.error(f"Exceeded maximum retries ({max_retries}) for command: {command}")
        return False

    def _verify_click_success(self, x: int, y: int) -> bool:
        """
        Verify that the click action was successful by checking the UI state.
        
        Args:
            x (int): The X coordinate where the click was performed.
            y (int): The Y coordinate where the click was performed.
        
        Returns:
            bool: True if the click was successful, False otherwise.
        """
        # Example verification logic: Check if the mouse is still at the expected position
        current_x, current_y = self.mouse.get_position()
        if (current_x, current_y) == (x, y):
            logging.info(f"Click verified at ({x}, {y}).")
            return True
        logging.warning(f"Mouse position after click is ({current_x}, {current_y}), expected ({x}, {y}).")
        return False

    def handle_move(self, command: str) -> bool:
        match = re.search(r"move to \((\d+),\s*(\d+)\)", command)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return self.move_to(x, y)
        logging.error(f"Invalid move command format: {command}")
        return False

    def handle_click(self, command: str) -> bool:
        match = re.search(r"click\s+button='(\w+)'", command)
        if match:
            button = match.group(1)
            return self.click(button=button)
        logging.error(f"Invalid click command format: {command}")
        return False

    def handle_scroll(self, command: str) -> bool:
        match = re.search(r"scroll\s+(up|down)\s+(\d+)", command)
        if match:
            direction, amount = match.group(1), int(match.group(2))
            return self.scroll(direction, amount)
        logging.error(f"Invalid scroll command format: {command}")
        return False

    def _regenerate_command(self) -> Optional[str]:
        """
        Regenerate the command using TextAgent when the previous command fails.
        
        Returns:
            Optional[str]: The new command string or None if regeneration fails.
        """
        try:
            logging.debug("Attempting to regenerate command using TextAgent.")
            # Compose a prompt that includes mappings to guide TextAgent
            regeneration_prompt = (
                f"The previous command was invalid: '{self.current_command}'. "
                "Please provide a valid mouse command in one of the following exact formats: "
                "'move to (x, y)' or 'move to (x, y) and click'. Ensure there is no additional text."
                f"Distance Mappings: {self.distance_mappings}\n"
                f"Direction Mappings: {self.direction_mappings}\n"
                f"Position Mappings: {self.position_mappings}\n"
            )
            input_data = {
                "query": regeneration_prompt,
                "image": self.screen.get_screen_image()  # Assuming this method exists
            }
            # Generate a new command using the TextAgent with input_data
            new_command = self.text_agent.generate_command(input_data)
            logging.info(f"Regenerated command: {new_command}")
            return new_command
        except Exception as e:
            logging.error(f"Failed to regenerate command: {e}")
            return None

    def _verify_location(self, x: int, y: int) -> bool:
        """
        Verify that the mouse has moved to the specified location within the viewport.
        
        Args:
            x (int): The target X coordinate.
            y (int): The target Y coordinate.
        
        Returns:
            bool: True if the mouse is at the specified location, False otherwise.
        """
        current_x, current_y = self.mouse.get_position()
        if (current_x, current_y) == (x, y):
            logging.info(f"Mouse successfully moved to ({x}, {y}).")
            return True
        logging.warning(f"Mouse position after move is ({current_x}, {current_y}), expected ({x}, {y}).")
        return False

    def _validate_command_format(self, command: str) -> bool:
        """
        Validates the format of the incoming command.
        
        Args:
            command (str): The command string to validate.
        
        Returns:
            bool: True if the command format is valid, False otherwise.
        """
        # Expected format: "move to (x, y)" or "move to (x, y) and click"
        pattern = r"move to \(\d+, \d+\)( and click)?"
        if re.fullmatch(pattern, command.lower()):
            return True
        logging.warning(f"Received unexpected command format: {command}")
        return False

    def _extract_expected_element(self, command: str) -> Optional[str]:
        """
        Extracts the expected UI element from the command for verification.
        
        Args:
            command (str): The mouse command.
        
        Returns:
            Optional[str]: The expected UI element name.
        """
        # Updated to focus on "Continue in Browser" link
        match = re.search(r"Click 'Continue in Browser' link", command.lower())
        if match:
            return "Continue in Browser"
        return None

    def format_text_agent_response(self, response: str, annotated_image_path: str) -> Optional[str]:
        """
        Convert TextAgent's response into a structured NLP command.
        Ensures commands are within the viewport bounds.
        """
        pattern = r"^move to \((\d+), (\d+)\)( and click)?$"  # Capture x and y
        match = re.fullmatch(pattern, response.strip(), re.IGNORECASE)
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            click_action = " and click" if match.group(3) else ""
            
            # Clamp x and y to viewport bounds
            x = max(0, min(x, self.CUSTOM_VIEWPORT_WIDTH))
            y = max(0, min(y, self.CUSTOM_VIEWPORT_HEIGHT))
            
            command = f"move to ({x}, {y}){click_action}"
            logging.debug(f"Formatted NLP command: {command}")
            return command
        else:
            logging.error(f"Command does not match expected format: {response}")
            # Attempt to handle the error using ErrorController with a clarification prompt
            def retry_callback():
                clarification_command = self._clarify_text_agent_response(response, annotated_image_path)
                if clarification_command:
                    formatted_command = self.format_text_agent_response(clarification_command, annotated_image_path)
                    if formatted_command:
                        return formatted_command
                return None

            handled = self.error_controller.handle_error(
                error=ValueError("Invalid command format"),
                context="format_text_agent_response",
                retry_callback=retry_callback
            )
            
            if not handled:
                logging.error("All retry attempts failed for parsing TextAgent response.")
                # Instead of returning None, return a safe default command or skip
                return None  # Alternatively, could return a default safe command
            return retry_callback()

    def _clarify_text_agent_response(self, original_response: str, annotated_image_path: str) -> Optional[str]:
        """
        Sends a clarification request to the TextAgent to obtain a valid command.
        """
        clarification_prompt = (
            f"The previous response was not in the expected format. Please provide the command to "
            f"move the mouse in the following exact format: 'move to (x, y)' or 'move to (x, y) and click'.\n"
            f"Original response: \"{original_response}\""
        )
        try:
            clarification = self.text_agent.complete_task({
                "image": annotated_image_path,
                "query": clarification_prompt
            })
            logging.debug(f"Clarification from TextAgent: {clarification}")
            # Attempt to parse the clarification response
            match = re.fullmatch(r"move to \((\d+),\s*(\d+)\)( and click)?", clarification.strip(), re.IGNORECASE)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                click_action = " and click" if match.group(3) else ""
                command = f"move to ({x}, {y}){click_action}"
                return command
            else:
                logging.error(f"Clarification response did not match expected format: {clarification}")
                return None
        except Exception as e:
            logging.error(f"Error during clarification of TextAgent response: {e}")
            return None

    def scroll(self, direction: str, amount: int) -> bool:
        """
        Perform a scroll action.
        
        Args:
            direction (str): Direction to scroll ('up' or 'down').
            amount (int): Amount to scroll.
        
        Returns:
            bool: True if scrolling was successful.
        """
        try:
            if direction == "up":
                self.mouse.scroll(0, amount)
            elif direction == "down":
                self.mouse.scroll(0, -amount)
            else:
                logging.error(f"Invalid scroll direction: {direction}")
                return False
            logging.debug(f"Scrolled {direction} by {amount} units.")
            return True
        except Exception as e:
            logging.error(f"Error during scrolling: {e}")
            return False

    def parse_command(self, command: str) -> Optional[Tuple[int, int, Optional[str]]]:
        """
        Parses a machine-readable command into actionable instructions.
        
        Args:
            command (str): The command string to parse.
        
        Returns:
            Optional[Tuple[int, int, Optional[str]]]: Parsed x, y coordinates and an optional action.
        """
        match = re.fullmatch(r"move to \(\s*(\d+)\s*,\s*(\d+)\s*\)(?:\s+and\s+(click|double-click|right-click))?", command.lower())
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            action = match.group(3) if match.group(3) else None
            return (x, y, action)
        else:
            logging.error(f"Command does not match expected format: {command}")
            return None

    def decide_next_action(self, enhanced_image, mouse_position, prompt: str) -> str:
        """
        Decide the next mouse action based on the enhanced prompt and predefined mappings.
        
        Args:
            enhanced_image (numpy.ndarray): The enhanced image from Agent.
            mouse_position (tuple): Current mouse position.
            prompt (str): The enhanced prompt from ManagerAgent.
        
        Returns:
            str: The next action command.
        """
        input_data = {
            "query": self._compose_prompt(prompt, mouse_position),
            "image": enhanced_image
        }
        return self.complete_task(input_data)
    
    def _compose_prompt(self, prompt: str, mouse_position: tuple) -> str:
        """
        Compose a detailed prompt that includes movement and direction mappings.
        
        Args:
            prompt (str): The task prompt.
            mouse_position (tuple): Current mouse position.
        
        Returns:
            str: The composed prompt for TextAgent.
        """
        screen_width = self.screen.width
        screen_height = self.screen.height
        mappings_info = (
            f"Distance Mappings: {self.distance_mappings}\n"
            f"Direction Mappings: {self.direction_mappings}\n"
            f"Position Mappings: {self.position_mappings}\n"
            f"Screen Width: {screen_width}\n"
            f"Screen Height: {screen_height}\n"
        )
        full_prompt = (
            f"{mappings_info}\n"
            f"Task: {prompt}\n"
            f"Current Mouse Position: {mouse_position}\n"
            "Generate a mouse command using the above mappings in one of the following formats exactly: "
            "'move to (x, y)' or 'move to (x, y) and click'."
        )
        return full_prompt

    def verify_successful_action(self, task, success, overlay_new_image, text_agent):
        prompt = (
            f"The current task is {task}. Command executed successfully: {success}.\n\n"
            "Is the task complete by displaying the login page? Reply yes or no."
        )
        response = text_agent.complete_task(input={"query": prompt, "image": overlay_new_image})   
        print(f"Response: {response}")
        return "yes" in response.strip().lower()  # Updated comparison to handle responses like "Yes."
