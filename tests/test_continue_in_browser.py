from computer.computer import Computer
import time
from agents.command_formatter import CommandFormatterAgent
from agents.text import TextAgent
from controllers.nlp_mouse_controller import NLPMouseController
from agents.manager import ManagerAgent
from overlay.overlay import Overlay
from computer.screen import Screen
from computer.mouse import Mouse
import cv2

def test_continue_in_browser(text_agent: TextAgent, nlp_mouse_controller: NLPMouseController, screen: Screen, mouse: Mouse):
    screen_image = screen.get_screen_image()
    history = []
    task = "Click 'Continue in Browser' link for Discord in the browser within the custom coordinate system."
    history.append({"task": task})
    time.sleep(10)  # Allow time for Computer to initialize
    screen_width, screen_height = screen.get_resolution()
    # Apply coordinate system overlay based on viewport size
    overlay = Overlay()
    overlay_image = overlay.add_coordinate_system(screen_image, screen_width, screen_height)
    x = 1

    # Get current mouse position and scale it to viewport dimensions
    mouse_pos = mouse.get_position()
    history.append({f"{x}_mouse_pos": mouse_pos})

    # Annotate with scaled mouse position
    overlay_image = overlay.annotate_mouse_position(overlay_image, mouse_pos)
    cv2.imwrite("overlay_image_with_mouse.png", overlay_image)

    # Generate next action within viewport bounds
    next_action = text_agent.decide_next_action("overlay_image_with_mouse.png", mouse.get_position(), task)
    success = nlp_mouse_controller.execute_command(next_action)

    time.sleep(5)
    new_screen_image = screen.get_screen_image()
    # Get current mouse position and scale it to viewport dimensions
    mouse_pos = mouse.get_position()
    history.append({f"{x}_mouse_pos": mouse_pos})
    # Apply coordinate system overlay to the new screen image
    overlay_new_image = overlay.add_coordinate_system(new_screen_image, screen_width, screen_height)
    # Annotate with scaled mouse position
    overlay_image = overlay.annotate_mouse_position(overlay_image, mouse_pos)
    cv2.imwrite("overlay_image_with_mouse_after_action.png", overlay_image)

    if not success:
        print(f"Executing command '{next_action}' failed.")
        # Verify the action was successful
    if not verify_successful_action(task, success, overlay_new_image, text_agent):
        print(f"Failed to complete action for {task}.")
        retry_task("overlay_image_with_mouse_after_action.png", history, text_agent, nlp_mouse_controller, screen, mouse)
        return
    print(f"mouse position: {mouse.get_position()}")
    print(f"Successfully completed action for {task}.")

def retry_task(overlay_new_image, history, text_agent, nlp_mouse_controller, screen, mouse):
    # Get current screen image
    screen_image = screen.get_screen_image()
    screen_width, screen_height = screen.get_resolution()
    overlay = Overlay()
    
    # Create new overlay image with coordinate system
    retry_overlay_image = overlay.add_coordinate_system(screen_image, screen_width, screen_height)
    
    # Annotate all previous mouse positions from history with X's
    for entry in history:
        for key, pos in entry.items():
            if "_mouse_pos" in key:
                retry_overlay_image = overlay.annotate_failed_attempt(retry_overlay_image, pos)
    
    # Annotate current mouse position
    current_pos = mouse.get_position()
    retry_overlay_image = overlay.annotate_mouse_position(retry_overlay_image, current_pos)
    
    # Save the annotated image
    cv2.imwrite("retry_overlay_image.png", retry_overlay_image)
    
    # Get next action based on history
    result = text_agent.decide_next_action_from_history("retry_overlay_image.png", history)
    success = nlp_mouse_controller.execute_command(result)
    
    if not success:
        print(f"Executing command '{result}' failed.")
        # Add failed attempt to history
        history.append({"failed_mouse_pos": current_pos})
        retry_task("retry_overlay_image.png", history, text_agent, nlp_mouse_controller, screen, mouse)
        return
    
    print(f"Successfully completed action for {history[0]['task']}")  # Get original task from history


def verify_successful_action(task, success, overlay_new_image, text_agent):
    prompt = f"The current task is {task}. command executed successfully: {success}.\n\nIs the task complete by displaying the login page? Reply yes or no."
    response = text_agent.complete_task(input={"query": prompt, "image": overlay_new_image})   
    print(f"Response: {response}")
    return "yes" in response.strip().lower()  # Updated comparison to handle responses like "Yes."

if __name__ == "__main__":
    computer = Computer()
    computer.run()
    screen = computer.screen
    mouse = computer.mouse
    text_agent = TextAgent()
    command_formatter = CommandFormatterAgent()
    nlp_mouse_controller = NLPMouseController(
        mouse=mouse,
        screen=screen,
        text_agent=text_agent,
        command_formatter=command_formatter
    )
    test_continue_in_browser(text_agent, nlp_mouse_controller, screen, mouse)

