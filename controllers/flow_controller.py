import logging
import traceback
import threading
import time
import sys
from typing import Optional
import cv2
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import re
from controllers.nlp_mouse_controller import NLPMouseController

class SpecificException(Exception):
    """Custom exception for specific errors in FlowController."""
    pass


class TaskProcessingError(Exception):
    """Exception raised when a task fails to process after retries."""
    pass


class FlowController:
    def __init__(self, vision_agent, text_agent, screen, mouse):
        self.vision_agent = vision_agent
        self.text_agent = text_agent
        self.screen = screen
        self.mouse = mouse
        self.task_queue = []
        self.queue_lock = threading.Lock()
        self.MAX_ITERATIONS = 5  # Maximum refinement attempts
        self.MAX_RETRIES = 3
        self.retry_delay = 2  # Initial delay in seconds
        self.metrics = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'average_processing_time': 0.0
        }
        self.shutdown_event = threading.Event()
        self.task_thread = None  # Initialize task_thread
        self.dead_letter_queue = []

        logging.debug(
            "FlowController initialized with vision_agent: %s, text_agent: %s, screen: %s, mouse: %s",
            self.vision_agent, self.text_agent, self.screen, self.mouse
        )

        self.nlp_mouse_controller = NLPMouseController(mouse, screen, vision_agent, text_agent)

    def add_task(self, task):
        with self.queue_lock:
            self.task_queue.append(task)
        logging.info(f"Task added: {task}")

    def run_tasks(self):
        logging.info("Starting task processing thread.")
        self.task_thread = threading.Thread(target=self._task_worker, daemon=False)  # Set daemon to False
        self.task_thread.start()

    def wait_for_completion(self):
        """Wait for the task processing thread to finish."""
        if self.task_thread:
            logging.info("Waiting for task processing to complete.")
            self.task_thread.join()
            logging.info("Task processing completed.")

    def _task_worker(self):
        logging.debug("Task worker thread started.")
        logging.info("Task worker thread is running.")
        while not self.shutdown_event.is_set():
            with self.queue_lock:
                if not self.task_queue:
                    logging.info("No more tasks to process. Waiting for new tasks...")
                    time.sleep(1)
                    continue
                task = self.task_queue.pop(0)
            try:
                logging.debug(f"Picked up task: {task} for processing.")
                start_time = time.time()
                self.process_task_with_retries(task)
                elapsed = time.time() - start_time
                self._update_metrics(elapsed)
                logging.info(f"Task '{task}' processed in {elapsed:.2f} seconds.")
                self.metrics['tasks_processed'] += 1
            except TaskProcessingError as e:
                self.metrics['tasks_failed'] += 1
                logging.error(f"Task '{task}' failed after retries: {e}", exc_info=True)
            except Exception as e:
                self.metrics['tasks_failed'] += 1
                logging.error(f"Unhandled exception for task '{task}': {e}", exc_info=True)
        logging.debug("Task worker thread exiting.")

    def process_task_with_retries(self, task):
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                self.process_task(task)
                return
            except TaskProcessingError as e:
                retries += 1
                delay = self.retry_delay * (2 ** (retries - 1))
                logging.warning(f"Retrying task '{task}' ({retries}/{self.MAX_RETRIES}) after error: {e}")
                time.sleep(delay)
        logging.error(f"Task '{task}' failed after {self.MAX_RETRIES} retries. Moving to dead-letter queue.")
        self.dead_letter_queue.append(task)

    def shutdown(self):
        logging.info("Shutdown signal received. Stopping task processing.")
        self.shutdown_event.set()

    def process_task(self, task):
        logging.info(f"Processing task: {task}")
        try:
            # Capture current screen image
            screen_image = self.screen.get_screen_image()
            
            # Step 1: Detect elements and add overlays
            scene_result = self.vision_agent.understand_scene(image=screen_image, task=task)
            
            if scene_result['status'] != 'success':
                logging.error(f"Failed to process task '{task}': {scene_result['message']}")
                raise TaskProcessingError(scene_result['message'])
            
            # Add overlays to the screenshot
            overlay_image = scene_result.get('overlay_image')
            
            # Save the annotated image and get the file path
            annotated_image_path = self._save_annotated_image(overlay_image, "overlay_label")
            
            # Step 2: Generate and execute NLP commands iteratively
            while True:
                # Retrieve text results to generate command
                command_response = scene_result.get('text_results')
                if not command_response:
                    logging.error("No command response received from TextAgent.")
                    break  # Exit if no command is available
                
                # Format the TextAgent's response into a command
                formatted_command = self.format_text_agent_response(command_response, annotated_image_path)
                if not formatted_command:
                    logging.error("Formatted command is invalid.")
                    break  # Exit if the command is invalid
                
                # Execute the mouse command
                success = self.nlp_mouse_controller.execute_command(formatted_command)
                if not success:
                    logging.error("Failed to execute command.")
                    break  # Exit if command execution fails
                
                logging.debug(f"Executed command: {formatted_command}")
                
                # Verify if the task is complete
                if self._is_task_complete():
                    logging.info(f"Task '{task}' completed successfully.")
                    break  # Exit the loop if task is complete
                
                # Optionally, capture a new screenshot and update scene_result for the next iteration
                screen_image = self.screen.get_screen_image()
                scene_result = self.vision_agent.understand_scene(image=screen_image, task=task)
        
        except TaskProcessingError as e:
            self.metrics['tasks_failed'] += 1
            logging.error(f"Task '{task}' failed: {e}")
        except Exception as e:
            self.metrics['tasks_failed'] += 1
            logging.error(f"Unexpected error during task '{task}': {e}")
            logging.debug(traceback.format_exc())
    
    def _is_task_complete(self) -> bool:
        """
        Determine if the current task has been completed.
        
        Returns:
            bool: True if the task is complete, False otherwise.
        """
        # Implement logic to verify task completion
        # This could involve checking specific UI elements or system states
        # For example:
        # return self.vision_agent.check_completion_condition()
        return True  # Placeholder implementation

    def _update_metrics(self, processing_time: float):
        """Update performance metrics."""
        total = self.metrics['tasks_processed'] + self.metrics['tasks_failed']
        if total == 0:
            self.metrics['average_processing_time'] = processing_time
        else:
            current_avg = self.metrics['average_processing_time']
            new_avg = (current_avg * (total - 1) + processing_time) / total
            self.metrics['average_processing_time'] = new_avg
        logging.info(f"Metrics Update: {self.metrics}")

    def _generate_dynamic_prompt(self, task_description):
        """Generate a dynamic prompt based on the task description for UI element detection."""
        prompt = f"Detect all relevant UI elements necessary to perform the following task: '{task_description}'. " \
                 "Pay special attention to text labels, buttons, and input fields that are pertinent to executing the task."
        logging.debug(f"Dynamic prompt generated: {prompt}")
        return prompt

    def _ensure_query_field(self, command, description):
        """
        Ensures that the command is a dictionary containing a 'query' field.
        If the command is a string, it wraps it in a dictionary.
        """
        if isinstance(command, str):
            logging.debug(f"Command for '{description}' is a string. Wrapping in a dictionary with 'query' field.")
            command = {'query': command}
        elif isinstance(command, dict):
            if 'query' not in command:
                logging.debug(f"Command for '{description}' is a dict but missing 'query'. Adding empty 'query' field.")
                command['query'] = ""
        else:
            logging.error(f"Command for '{description}' is neither a string nor a dict. Received type: {type(command)}")
            logging.debug(f"Received command of unexpected type: {type(command)} with content: {command}")
            raise ValueError(f"Invalid command type for '{description}'. Expected str or dict.")
        
        logging.debug(f"Ensured 'query' field for '{description}': {command}")
        
        return command

    def _log_command(self, step, command):
        """
        Logs the command details for debugging purposes.
        """
        logging.info(f"Executing Step: {step}")
        logging.debug(f"Command Details: {command}")

    def _validate_command(self, command, description):
        """
        Validates that the command contains a 'query' field.
        Logs an error and raises TaskProcessingError if not.
        """
        if not isinstance(command, dict):
            logging.error(f"Command for '{description}' is not a dictionary: {command}")
            logging.debug(f"Invalid command type: {type(command)} for description: '{description}'")
            raise TaskProcessingError(f"Command for '{description}' must be a dictionary containing a 'query' field.")
        if 'query' not in command:
            logging.error(f"Command for '{description}' missing 'query' field: {command}")
            logging.debug(f"Full command data: {command}")
            raise TaskProcessingError(f"Command for '{description}' missing 'query' field.")
        if not command['query']:
            logging.warning(f"Command for '{description}' has an empty 'query' field: {command}")
        logging.debug(f"Validated command for '{description}': {command}")

    def _join_agora_discord_voice_channel(self) -> bool:
        """
        Steps to join the Agora Discord Voice Channel with enhanced vision capabilities.
        """
        try:
            logging.info("Starting task: Join Agora Discord Voice Channel")
            
            # Step 0: Click "Continue in Browser" link
            self._click_element("Continue in Browser")
            
            # Step 1: Navigate to Discord URL
            self._click_element("Navigate to Discord Website")
            
            # Step 2: Login if necessary
            if self.vision_agent.verify_element("login_page", timeout=10):
                self._input_text("Enter Discord Username", "YourUsername")
                self._input_text("Enter Discord Password", "YourPassword")
            
            # Step 3: Navigate to Voice Channel
            self._click_element("Navigate to Agora Voice Channel")
            
            # Step 4: Join Voice Channel
            self._click_element("Join Agora Voice Channel")
            
            # Step 5: Verify Successful Joining
            if not self.vision_agent.verify_element("joined_agora_voice", timeout=10):
                raise TaskProcessingError("Failed to join Agora Discord Voice Channel.")
            
            logging.info("Task 'Join Agora Discord Voice Channel' completed successfully.")
            return True
        except TaskProcessingError as e:
            self.metrics['tasks_failed'] += 1
            logging.error(f"Task failed: {e}", exc_info=True)
            return False
        except Exception as e:
            self.metrics['tasks_failed'] += 1
            logging.error(f"Unexpected error: {e}", exc_info=True)
            return False

    def _click_element(self, element_description: str):
        """
        Locate an element using VisionAgent, overlay bounding box, and perform a mouse click.
        """
        logging.info(f"Attempting to click element: {element_description}")
        screen_image = self.screen.get_screen_image()
        detection = self.vision_agent.find_element(screen_image, element_description)
        
        if not detection.get('element_found'):
            raise TaskProcessingError(f"Element '{element_description}' not found.")
        
        bbox = detection['element_details']['bbox']
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        
        # Overlay bounding box and coordinates on the image
        annotated_image = self._overlay_bounding_box(screen_image, bbox, element_description, center_x, center_y)
        
        # Save or process the annotated image as needed
        annotated_image_path = self._save_annotated_image(annotated_image, element_description)
        
        # Use TextAgent's complete_task to interpret the annotated image and generate the command
        command = self.text_agent.complete_task({
            "image": annotated_image_path,
            "query": (
                f"Generate a machine-readable command to move the mouse to the center of the '{element_description}' "
                "element and perform a click action. The command should be in the format: 'move to (x, y) and click'."
            )
        })
        
        if not self._is_valid_command(command):
            logging.error(f"Invalid command received from TextAgent: {command}")
            raise TaskProcessingError(f"Invalid command format: {command}")
        
        logging.debug(f"Generated command from TextAgent: {command}")
        
        success = self.nlp_mouse_controller.execute_command(command)
        if not success:
            raise TaskProcessingError(f"Failed to execute command for '{element_description}'.")
        
        logging.info(f"Clicked on element: {element_description}")

    def _input_text(self, field_description: str, text: str):
        """
        Locate a text input field, overlay bounding box, enter the specified text.
        """
        logging.info(f"Entering text into: {field_description}")
        screen_image = self.screen.get_screen_image()
        detection = self.vision_agent.find_element(screen_image, field_description)
        
        if not detection.get('element_found'):
            raise TaskProcessingError(f"Input field '{field_description}' not found.")
        
        bbox = detection['element_details']['bbox']
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        
        # Overlay bounding box and coordinates on the image
        annotated_image = self._overlay_bounding_box(screen_image, bbox, field_description, center_x, center_y)
        
        # Save or process the annotated image as needed
        annotated_image_path = self._save_annotated_image(annotated_image, field_description)
        
        # Use TextAgent's complete_task to interpret the annotated image and generate the move command
        move_command = self.text_agent.complete_task({
            "image": annotated_image_path,
            "query": f"Move the mouse to the center of the '{field_description}' input field."
        })
        
        # Generate the type command
        type_command = f"type '{text}'"
        
        logging.debug(f"Generated move command from TextAgent: {move_command}")
        logging.debug(f"Generated type command: {type_command}")
        
        # Execute the move command
        success_move = self.nlp_mouse_controller.execute_command(move_command)
        if not success_move:
            raise TaskProcessingError(f"Failed to move to input field '{field_description}'.")
        
        # Execute the type command using complete_task
        success_type = self.text_agent.complete_task({
            "query": type_command
        })
        if not success_type:
            raise TaskProcessingError(f"Failed to type into input field '{field_description}'.")
        
        logging.info(f"Entered text into: {field_description}")

    def _overlay_bounding_box(self, image, bbox, label, center_x, center_y) -> Image.Image:
        """
        Overlay bounding box and coordinates on the image.
        
        Args:
            image: Original screen image.
            bbox: Bounding box coordinates.
            label: Description label for the bounding box.
            center_x: X-coordinate of the center point.
            center_y: Y-coordinate of the center point.
        
        Returns:
            Image with overlaid bounding box and coordinates.
        """
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        # Draw bounding box
        draw.rectangle(bbox, outline="red", width=2)
        # Add label
        font = ImageFont.load_default()
        text = f"{label}: ({center_x}, {center_y})"
        draw.text((bbox[0], bbox[1] - 10), text, fill="red", font=font)
        return pil_image

    def _save_annotated_image(self, pil_image: Image.Image, label: str) -> str:
        """
        Save the annotated image to a temporary file and return the file path.
        
        Args:
            pil_image: PIL Image with annotations.
            label: Label for the annotation.
        
        Returns:
            Path to the saved annotated image.
        """
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        filename = f"annotated_{label.replace(' ', '_')}_{timestamp}.png"
        file_path = os.path.join(temp_dir, filename)
        pil_image.save(file_path)
        logging.debug(f"Annotated image saved to {file_path}")
        return file_path

    def _is_valid_command(self, command, description, annotated_image_path):
        """
        Validates that the command is a proper movement and action command.
        """
        pattern = r"move to \(\d+, \d+\)( and click)?"
        if re.fullmatch(pattern, command.lower()):
            return True
        logging.warning(f"Received unexpected command format: {command}")
        
        # Send command list to TextAgent for better understanding
        command_list = self._get_allowed_commands()
        response = self.text_agent.complete_task({
            "image": annotated_image_path,
            "commands": command_list,
            "query": f"The following command was invalid: '{command}'. Please provide a valid command from the list below."
        })
        logging.debug("Sent command list to TextAgent for invalid command handling.")
        
        return False

    def format_text_agent_response(self, response: str, annotated_image_path: str) -> Optional[str]:
        """
        Convert TextAgent's response into a structured NLP command.
        Enhanced to handle unexpected formats and attempt clarification.
        """
        pattern = r"move(?:\s+cursor)?\s+to\s*\(?(\d+),\s*(\d+)\)?(?:\s+and\s+click)?"
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            x = match.group(1)
            y = match.group(2)
            click_action = " and click" if re.search(r"and\s+click", response, re.IGNORECASE) else ""
            command = f"move to ({x}, {y}){click_action}"
            logging.debug(f"Formatted NLP command: {command}")
            return command
        else:
            logging.error(f"Failed to parse TextAgent response: {response}")
            # Attempt to clarify the response
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
            f"move the mouse in the following format: 'move to (x, y)' or 'move to (x, y) and click'.\n"
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
                click_action = " and click" if re.search(r"and\s+click", clarification, re.IGNORECASE) else ""
                command = f"move to ({x}, {y}){click_action}"
                return command
            else:
                logging.error(f"Clarification response did not match expected format: {clarification}")
                return None
        except Exception as e:
            logging.error(f"Error during clarification of TextAgent response: {e}")
            return None

    def _get_allowed_commands(self) -> list:
        """
        Returns a list of allowed commands for the TextAgent.
        
        Returns:
            list: A list of valid command strings.
        """
        return [
            "move to (x, y)",
            "move to (x, y) and click",
            "type 'text'",
            "scroll up",
            "scroll down"
            # Add other valid commands as needed
        ]

