from typing import Tuple, Optional
import re
import logging
import time  # Import time for adding delays

class NLPMouseController:
    """
    A controller that translates natural language commands into mouse movements.
    """
    def __init__(self, mouse, screen, vision_agent, text_agent):
        self.mouse = mouse
        self.screen = screen
        self.vision_agent = vision_agent
        self.text_agent = text_agent
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
        self.max_regeneration_attempts = 3  # Maximum regeneration attempts
        self.regeneration_count = 0  # Counter for regeneration attempts

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
        Execute a mouse command with verification using VisionAgent.
        
        Args:
            command (str): The command to execute.
        
        Returns:
            bool: True if command executed and verified successfully.
        """
        self.current_command = command  # Set the current command
        self.current_context = {
            "screen_size": (self.screen.width, self.screen.height),
            "last_action": "mouse_click" if "and click" in command.lower() else "mouse_move",
            # Add more contextual information as needed
        }
        self.regeneration_count = 0     # Reset regeneration counter
        
        try:
            # Initialize a loop to handle recursive commands
            while command and self.regeneration_count < self.max_regeneration_attempts:
                logging.debug(f"Executing command: {command} (Attempt {self.regeneration_count + 1})")
                
                # Validate the command format
                if not self._validate_command_format(command):
                    logging.error(f"Command format invalid: {command}")
                    # Attempt to regenerate the command using TextAgent
                    command = self._regenerate_command()
                    if not command:
                        logging.error("Failed to regenerate command due to invalid format.")
                        return False
                    self.regeneration_count += 1
                    continue
                
                movement = self.parse_movement(command)
                if not movement:
                    logging.error(f"Failed to parse movement from command: {command}")
                    # Attempt to regenerate the command using TextAgent
                    command = self._regenerate_command()
                    if not command:
                        logging.error("Failed to regenerate command due to movement parsing failure.")
                        return False
                    self.regeneration_count += 1
                    continue
                    
                # Unpack absolute positions
                target_x, target_y = movement
                
                # Execute movement to absolute position
                try:
                    move_success = self.mouse.move_to(target_x, target_y)
                    if not move_success:
                        logging.error(f"Mouse movement failed for command: {command}")
                        # Attempt to regenerate the command using TextAgent
                        command = self._regenerate_command()
                        if not command:
                            logging.error("Failed to regenerate command after mouse movement failure.")
                            return False
                        self.regeneration_count += 1
                        continue
                    logging.debug(f"Mouse moved to ({target_x}, {target_y}) successfully.")
                except Exception as e:
                    logging.exception(f"Exception during mouse.move_to({target_x}, {target_y}): {e}")
                    # Attempt to regenerate the command using TextAgent
                    command = self._regenerate_command()
                    if not command:
                        logging.error("Failed to regenerate command after mouse.move_to exception.")
                        return False
                    self.regeneration_count += 1
                    continue
                
                # Add a short delay to ensure mouse movement is registered
                time.sleep(0.2)
                
                # Perform click action if specified
                if "and click" in command.lower():
                    try:
                        click_success = self.mouse.click()
                        if not click_success:
                            logging.error("Mouse click action failed.")
                            # Attempt to regenerate the command using TextAgent
                            command = self._regenerate_command()
                            if not command:
                                logging.error("Failed to regenerate command after mouse click failure.")
                                return False
                            self.regeneration_count += 1
                            continue
                        logging.debug("Mouse click action executed successfully.")
                    except Exception as e:
                        logging.exception(f"Exception during mouse.click(): {e}")
                        # Attempt to regenerate the command using TextAgent
                        command = self._regenerate_command()
                        if not command:
                            logging.error("Failed to regenerate command after mouse.click exception.")
                            return False
                        self.regeneration_count += 1
                        continue
                    
                    # Add a short delay after clicking
                    time.sleep(0.2)
                
                # Verify the current location
                try:
                    if not self._verify_location(target_x, target_y):
                        logging.error("Location verification failed.")
                        # Attempt to regenerate the command using TextAgent
                        command = self._regenerate_command()
                        if not command:
                            logging.error("Failed to regenerate command after location verification failure.")
                            return False
                        self.regeneration_count += 1
                        continue
                except Exception as e:
                    logging.exception(f"Exception during location verification: {e}")
                    # Attempt to regenerate the command using TextAgent
                    command = self._regenerate_command()
                    if not command:
                        logging.error("Failed to regenerate command after location verification exception.")
                        return False
                    self.regeneration_count += 1
                    continue
                
                # If all steps are successful
                logging.info(f"Command '{command}' executed successfully.")
                return True
            
            # If max regeneration attempts reached
            if self.regeneration_count >= self.max_regeneration_attempts:
                logging.error(f"Exceeded maximum regeneration attempts for command: {self.current_command}")
            return False
        except Exception as e:
            logging.exception(f"Error executing command '{command}': {e}")
            return False

    def _regenerate_command(self) -> Optional[str]:
        """
        Regenerate the command using TextAgent when the previous command fails.
        
        Returns:
            Optional[str]: The new command string or None if regeneration fails.
        """
        try:
            logging.debug("Attempting to regenerate command using TextAgent.")
            # Construct the required input_data for generate_command with 'query'
            input_data = {
                "query": (
                    f"Regenerate the mouse command based strictly on the failed command: '{self.current_command}'. "
                    "Ensure the command is in one of the following formats exactly: 'move to (x, y)' or 'move to (x, y) and click'."
                ),
                "last_command": self.current_command,  # Pass the last failed command
                "context": self.current_context         # Pass any relevant context
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
        Verify that the mouse has moved to the specified location.
        
        Args:
            x (int): The target X coordinate.
            y (int): The target Y coordinate.
        
        Returns:
            bool: True if the mouse is at the specified location, False otherwise.
        """
        current_x, current_y = self.mouse.get_position()
        if abs(current_x - x) <= self.mouse.movement_tolerance and abs(current_y - y) <= self.mouse.movement_tolerance:
            logging.info(f"Mouse successfully moved to ({x}, {y}).")
            return True
        logging.warning(f"Mouse not at the expected position. Current: ({current_x}, {current_y}), Expected: ({x}, {y})")
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
        # Example implementation, adjust based on actual command structure
        match = re.search(r"Click (\w+) button", command.lower())
        if match:
            return match.group(1)
        return None

    def format_text_agent_response(self, response: str, annotated_image_path: str) -> Optional[str]:
        """
        Convert TextAgent's response into a structured NLP command.
        Enhanced to handle unexpected formats and attempt clarification.
        """
        # First attempt to extract command using the existing pattern
        pattern = r"move(?:\s+cursor)?\s+to\s*\(?(\d+),\s*(\d+)\)?(?:\s+and\s+click)?"
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            x = match.group(1)
            y = match.group(2)
            click_action = ""
            if re.search(r"and\s+click", response, re.IGNORECASE):
                click_action = " and click"
            command = f"move to ({x}, {y}){click_action}"
            logging.debug(f"Formatted NLP command: {command}")
            return command
        else:
            # Attempt to extract commands if multiple steps are provided
            lines = response.split('\n')
            for line in lines:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    x = match.group(1)
                    y = match.group(2)
                    click_action = ""
                    if re.search(r"and\s+click", line, re.IGNORECASE):
                        click_action = " and click"
                    command = f"move to ({x}, {y}){click_action}"
                    logging.debug(f"Extracted NLP command from lines: {command}")
                    return command
            # If no valid command found, attempt clarification
            logging.error(f"Failed to parse TextAgent response: {response}")
            clarification_command = self._clarify_text_agent_response(response, annotated_image_path)
            if clarification_command:
                logging.debug(f"Clarified command: {clarification_command}")
                return clarification_command
            return None

    def _clarify_text_agent_response(self, original_response: str, annotated_image_path: str) -> Optional[str]:
        """
        Sends a clarification request to the TextAgent to obtain a valid command.
        """
        clarification_prompt = (
            f"The previous response was not in the expected format. Please provide the command to "
            f"move the mouse in the following format exactly: 'move to (x, y)' or 'move to (x, y) and click'.\n"
            f"Original response: \"{original_response}\""
        )
        try:
            clarification = self.text_agent.complete_task({
                "image": annotated_image_path,
                "query": clarification_prompt
            })
            logging.debug(f"Clarification from TextAgent: {clarification}")
            # Attempt to parse the clarification response
            match = re.search(r"move\s+to\s*\(?(\d+),\s*(\d+)\)?(?:\s+and\s+click)?", clarification, re.IGNORECASE)
            if match:
                x = match.group(1)
                y = match.group(2)
                click_action = ""
                if re.search(r"and\s+click", clarification, re.IGNORECASE):
                    click_action = " and click"
                command = f"move to ({x}, {y}){click_action}"
                return command
            else:
                logging.error(f"Clarification response did not match expected format: {clarification}")
                return None
        except Exception as e:
            logging.error(f"Error during clarification of TextAgent response: {e}")
            return None
