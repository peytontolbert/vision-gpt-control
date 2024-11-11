from test_continue_in_browser import test_continue_in_browser, verify_successful_action, retry_task
from computer.computer import Computer
from agents.text import TextAgent
from controllers.nlp_mouse_controller import NLPMouseController
from agents.manager import ManagerAgent
from overlay.overlay import Overlay
from computer.screen import Screen
from agents.command_formatter import CommandFormatterAgent
from computer.mouse import Mouse
from typing import Tuple, Dict, List
import time
import cv2
import logging

logging.basicConfig(level=logging.INFO)

def test_clicking_user_field(text_agent: TextAgent, nlp_mouse_controller: NLPMouseController, 
                           screen: Screen, mouse: Mouse, overlay: Overlay, computer: Computer):
    # Initialize browser
    success = test_continue_in_browser(text_agent, nlp_mouse_controller, screen, mouse, overlay, computer)
    if not success:
        logging.error("Failed to continue in browser")
        return False

    browser = computer.apps['browser']
    screen_width, screen_height = screen.get_resolution()
    movement_history = []
    task = "move the mouse and click the user field in the browser"
    
    # Allow proper initialization
    time.sleep(5)

    # Create initial overlay with coordinate system
    screen_image = screen.get_screen_image()
    overlay_image = overlay.add_coordinate_system(screen_image, screen_width, screen_height)
    
    # Get and verify initial position
    initial_pos = mouse.get_position()
    overlay_image = overlay.annotate_mouse_position(overlay_image, initial_pos)
    cv2.imwrite("initial_user_position.png", overlay_image)
    
    # Enhanced movement planning
    manager = ManagerAgent(text_agent)
    
    # Get movement command
    next_action = text_agent.decide_next_action(
        "initial_position.png", 
        initial_pos, 
        task
    )
    
            # Execute and verify movement
    success = nlp_mouse_controller.execute_command(next_action)

    # Create initial overlay with coordinate system
    screen_image = screen.get_screen_image()
    overlay_image = overlay.add_coordinate_system(screen_image, screen_width, screen_height)
    
    # Get and verify initial position
    initial_pos = mouse.get_position()
    overlay_image = overlay.annotate_mouse_position(overlay_image, initial_pos)
    cv2.imwrite("final_user_position.png", overlay_image)
    
    if not success:
        return False

    logging.info(f"Final mouse position: {mouse.get_position()}")
    logging.info(f"Successfully completed action for {task}")
    return True

if __name__ == "__main__":
    computer = Computer()
    computer.run()
    screen = computer.screen
    mouse = computer.mouse
    text_agent = TextAgent()
    overlay = Overlay()
    
    command_formatter = CommandFormatterAgent()
    nlp_mouse_controller = NLPMouseController(
        mouse=mouse,
        screen=screen,
        text_agent=text_agent,
        command_formatter=command_formatter
    )
    test_clicking_user_field(text_agent, nlp_mouse_controller, screen, mouse, overlay, computer)

