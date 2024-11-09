from test_continue_in_browser import test_continue_in_browser
from dotenv import load_dotenv
import os
from agents.manager import ManagerAgent
import time
import cv2
from overlay.overlay import Overlay
load_dotenv()
from computer.computer import Computer
from agents.text import TextAgent
from agents.command_formatter import CommandFormatterAgent
from controllers.nlp_mouse_controller import NLPMouseController
from controllers.error_controller import ErrorController
import logging

DISCORD_USER = os.getenv("DISCORD_USER")
DISCORD_PASS = os.getenv("DISCORD_PASS")

def test_login(task, DISCORD_USER, DISCORD_PASS, text_agent: TextAgent, nlp_mouse_controller: NLPMouseController, computer: Computer):
    # Initialize metadata, ManagerAgent, and overlay_image
    metadata = {
        "User": "Discord Automation",
        "Environment": "Login Page",
        "Action": "Enter Credentials",
        "DISCORD_USER": DISCORD_USER,
        "DISCORD_PASS": DISCORD_PASS
    }
    manager_agent = ManagerAgent(text_agent=text_agent)
    overlay = Overlay()
    screen = computer.screen
    new_screen_image = screen.get_screen_image()

    # Get screen dimensions
    screen_width = screen.width
    screen_height = screen.height

    overlay_image = overlay.add_coordinate_system(new_screen_image, screen_width, screen_height)
    mouse = computer.mouse
    mouse_position = mouse.get_position()
    actual_position = nlp_mouse_controller.custom_to_actual_coordinates(*mouse_position)
    cv2.circle(overlay_image, actual_position, radius=10, color=(0, 255, 0), thickness=-1)
    cv2.putText(overlay_image, f"Mouse: {mouse_position}", (actual_position[0] + 15, actual_position[1] + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imwrite("overlay_image_with_mouse.png", overlay_image)
    click_username_prompt = "Please click on the email/phone number field to activate it."
    # enhanced_prompt = manager_agent.enhance_prompt("click username field", metadata)
    next_action = text_agent.decide_next_action(overlay_image, mouse_position, click_username_prompt)
    print(f"Next action (click username): {next_action}")
    click_username_prompt = "Ensure the mouse is over the email/phone number field."
    success = verify_action_success(click_username_prompt, mouse, overlay_image, nlp_mouse_controller, manager_agent)
    print(f"verification success: {success}")
    # Initialize ErrorController
    error_controller = ErrorController()
    
    def retry_click_username():
        nonlocal next_action, success
        logging.info("Retrying to click the username field.")
        new_screen_image = screen.get_screen_image()
        overlay_image = overlay.add_coordinate_system(new_screen_image, screen_width, screen_height)
        mouse = computer.mouse
        mouse_position = mouse.get_position()
        actual_position = nlp_mouse_controller.custom_to_actual_coordinates(*mouse_position)
        cv2.circle(overlay_image, actual_position, radius=10, color=(0, 255, 0), thickness=-1)
        cv2.putText(overlay_image, f"Mouse: {mouse_position}", (actual_position[0] + 15, actual_position[1] + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imwrite("overlay_image_with_mouse_retry.png", overlay_image)
        next_action = text_agent.decide_next_action(overlay_image, computer.mouse.get_position(), click_username_prompt)
        logging.debug(f"Retrying next action (click username): {next_action}")
        success = nlp_mouse_controller.execute_command(next_action)
        if not success:
            logging.error("Execute command failed during retry.")
    
    success = nlp_mouse_controller.execute_command(next_action)
    time.sleep(5)  # Wait for the field to become active
    
    if not success:
        error_controller.handle_error(
            error=RuntimeError("Failed to click on the username field."),
            context="Click Username Field",
            retry_callback=retry_click_username
        )
        if not success:
            print("Failed to click on the username field after retries.")
            return
    
    # New: Handle multi-step login
    if success:
        keyboard_success = computer.keyboard.type_text(DISCORD_USER)
        print(f"Executed keyboard command: typing username")
        
        # Verify username entry
        def retry_enter_username():
            nonlocal keyboard_success
            # {{ Added: Re-activate the username field by clicking on it }}
            click_username_prompt = "Please click on the email/phone number field to activate it."
            next_click_action = text_agent.decide_next_action(overlay_image, computer.mouse.get_position(), click_username_prompt)
            print(f"Retrying: Activating username field: {next_click_action}")
            success_click = nlp_mouse_controller.execute_command(next_click_action)
            time.sleep(2)  # Wait for activation
            if success_click:
                # Retry entering username
                keyboard_success = computer.keyboard.type_text(DISCORD_USER)
                print(f"Retrying keyboard command: typing username")
            else:
                keyboard_success = False

        if not verify_successful_action("enter username", keyboard_success, computer.screen.get_screen_image(), text_agent):
            error_controller.handle_error(
                error=RuntimeError("Failed to enter username."),
                context="Enter Username",
                retry_callback=retry_enter_username
            )
            if not keyboard_success:
                print("Failed to enter username after retries.")
                return

        # Step 6: Click on the password field to activate it
        click_password_prompt = "Please click on the password field to activate it."
        enhanced_prompt = manager_agent.enhance_prompt("click password field", metadata)
        next_action = text_agent.decide_next_action(overlay_image, computer.mouse.get_position(), enhanced_prompt)
        print(f"Next action (click password): {next_action}")
        nlp_mouse_controller.execute_command(next_action)
        time.sleep(2)  # Wait for the field to become active
        
        success = verify_action_success(click_password_prompt, mouse, overlay_image, nlp_mouse_controller, manager_agent)
        # Step 7: Enter password using Keyboard
        enhanced_prompt = manager_agent.enhance_prompt("enter password", metadata)
        next_action = text_agent.decide_next_action(overlay_image, computer.mouse.get_position(), enhanced_prompt)
        print(f"Next action (password): {next_action}")
        keyboard_success = computer.keyboard.type_text(DISCORD_PASS)
        print(f"Executed keyboard command: typing password")
        
        # Verify password entry
        def retry_enter_password():
            nonlocal keyboard_success
            # {{ Added: Re-activate the password field by clicking on it }}
            click_password_prompt = "Please click on the password field to activate it."
            enhanced_click_prompt = manager_agent.enhance_prompt("click password field", metadata)
            next_click_action = text_agent.decide_next_action(overlay_image, computer.mouse.get_position(), click_password_prompt)
            print(f"Retrying: Activating password field: {next_click_action}")
            success_click = nlp_mouse_controller.execute_command(next_click_action)
            time.sleep(2)  # Wait for activation
            if success_click:
                # Retry entering password
                keyboard_success = computer.keyboard.type_text(DISCORD_PASS)
                print(f"Retrying keyboard command: typing password")
            else:
                keyboard_success = False

        if not verify_successful_action("enter password", keyboard_success, computer.screen.get_screen_image(), text_agent):
            error_controller.handle_error(
                error=RuntimeError("Failed to enter password."),
                context="Enter Password",
                retry_callback=retry_enter_password
            )
            if not keyboard_success:
                print("Failed to enter password after retries.")
                return

        # New: Submit login using Mouse
        submit_prompt = "Please click the Discord login button to submit your credentials."
        enhanced_prompt = manager_agent.enhance_prompt("submit login", metadata)
        next_action = text_agent.decide_next_action(overlay_image, computer.mouse.get_position(), submit_prompt)
        print(f"Next action (submit login): {next_action}")
        submit_success = nlp_mouse_controller.execute_command(next_action)
        print(f"Executed submit command: {next_action}")

        # Verify login submission
        if not verify_successful_action("submit login", submit_success, computer.screen.get_screen_image(), text_agent):
            print("Failed to submit login.")
            return

    print(f"Executed command: {next_action}")
    time.sleep(5)
    new_screen_image = computer.screen.get_screen_image()

    if not success:
        print(f"Executing command '{next_action}' failed.")
            # Verify the action was successful
    if not verify_successful_action(task, success, new_screen_image, text_agent):
        print(f"Failed to complete action for {task}.")
        return
    
    print(f"Successfully completed action for {task}.")
    return computer, text_agent, nlp_mouse_controller, new_screen_image

def verify_successful_action(task, success, new_screen_image, text_agent):
    prompt = f"The current task is {task}. command executed successfully: {success}.\n\nIs the task complete by a successful login? Reply yes or no."
    response = text_agent.complete_task(input={"query": prompt, "image": new_screen_image})   
    print(f"Response: {response}")
    return "yes" in response.strip().lower() # Updated comparison to handle responses like "Yes."


def verify_action_success(prompt, mouse, overlay_image, nlp_mouse_controller, manager_agent):
    mouse_position = mouse.get_position()
    actual_position = nlp_mouse_controller.custom_to_actual_coordinates(*mouse_position)
    cv2.circle(overlay_image, actual_position, radius=10, color=(0, 255, 0), thickness=-1)
    cv2.putText(overlay_image, f"Mouse: {mouse_position}", (actual_position[0] + 15, actual_position[1] + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imwrite("overlay_image_with_mouse_moved.png", overlay_image)
    success = manager_agent.verify_action("overlay_image_with_mouse_moved.png", prompt)
    return success


if __name__ == "__main__":
    task = "login to discord"
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
        command_formatter=command_formatter)
    test_continue_in_browser(text_agent, nlp_mouse_controller, screen, mouse)
    test_login(task=task, DISCORD_USER=DISCORD_USER, DISCORD_PASS=DISCORD_PASS, text_agent=text_agent, nlp_mouse_controller=nlp_mouse_controller, computer=computer)