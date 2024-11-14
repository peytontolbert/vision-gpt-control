from computer.qwen_browser import BrowserController
import time
from models.qwen2vl import Qwen2VL
import re
import json
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import os
import pyautogui  # For keyboard input
from agents.task_manager import TaskManager, Task

# Load environment variables
load_dotenv()

# Get Discord credentials
DISCORD_USER = os.getenv('DISCORD_USER')
DISCORD_PASS = os.getenv('DISCORD_PASS')

class MouseControllerHelper:
    def __init__(self, browser: BrowserController, qwen2vl: Qwen2VL):
        self.browser = browser
        self.qwen2vl = qwen2vl
        self.movement_history = []  # Track movement history for adaptive refinement

    def reset_history(self):
        self.movement_history = []

    def parse_coordinates(self, result):
        """Parse the x and y coordinates from the TextAgent result."""
        # Ensure result is a string
        if isinstance(result, list):
            result = ' '.join(result)
        elif not isinstance(result, str):
            print(f"Unexpected result type: {type(result)}")
            return None, None

        # Define regex patterns for different coordinate formats
        patterns = [
            r'\(x:\s*(\d+),\s*y:\s*(\d+)\)',  # Pattern: (x: 488, y: 552)
            r'\((\d+),\s*(\d+)\)'              # Pattern: (488, 552)
        ]

        for pattern in patterns:
            match = re.search(pattern, result)
            if match:
                # Get coordinates in screenshot space (1000x1000)
                screenshot_x, screenshot_y = map(int, match.groups())
                
                # Convert screenshot coordinates (1000x1000) to viewport coordinates
                viewport_x, viewport_y = self.browser.normalize_coordinates(
                    screenshot_x, 
                    screenshot_y, 
                    from_screenshot=True
                )
                
                print(f"Converting coordinates: Screenshot ({screenshot_x}, {screenshot_y}) -> Viewport ({viewport_x}, {viewport_y})")
                return int(screenshot_x), int(screenshot_y)

        print("No valid coordinates found in the result.")
        return None, None

    def locate_element_coordinates(self, element_name):
        """Ask the TextAgent to locate the precise coordinates of an element."""
        self.browser.take_screenshot("images/element_screenshot.png")
        result = self.qwen2vl.chat(input={
            "query": f"Please locate the center coordinates of:\n{element_name}\n reply with the exact coordinates as (x: , y: ) ",
            "image": "images/element_screenshot.png"
        })
        x, y = self.parse_coordinates(result)
        print(f"Located coordinates for '{element_name}': ({x}, {y})")
        return x, y

    def verify_mouse_position(self, viewport_x, viewport_y, element_name):
        """Verify mouse position with coordinate normalization."""
        self.browser.move_mouse_to(viewport_x, viewport_y)
        
        # Convert viewport coordinates back to screenshot coordinates for the filename
        #screenshot_x, screenshot_y = self.browser.normalize_coordinates(
        #    viewport_x, 
        #    viewport_y, 
        #    from_screenshot=False
        #)
        
        filename = f"images/mouse_position_{int(viewport_x)}_{int(viewport_y)}.png"
        self.browser.take_screenshot(filename)
        
        result = self.qwen2vl.chat(input={
            "query": f"""
Is '{element_name}' precisely highlighted with the red circle? Locate the red circle and ensure it is centered on {element_name}.
Reply with a JSON object containing:
- "confidence": a score between 0 and 100,
- "more_info": additional information about the verification.
Example:
{{"confidence": 85, "more_info": "Mouse is slightly to the left of the target."}}
            """,
            "image": filename
        })
        print(f"Verification result: {result}")
        try:
            # Updated parsing to handle list objects
            if isinstance(result, list) and len(result) > 0:
                data = json.loads(result[0].strip())
            elif isinstance(result, str):
                data = json.loads(result.strip())
            else:
                print(f"Unexpected result format: {result}")
                data = {}
            
            confidence = float(data.get("confidence", 0.0))
            more_info = data.get("more_info", "")
            # Include more_info in movement history for clearer instructions
            self.movement_history.append({"x": viewport_x, "y": viewport_y, "more_info": more_info})
        except (ValueError, json.JSONDecodeError):
            confidence = 0.0  # Default to 0 if parsing fails
            more_info = "Invalid response format."
            self.movement_history.append({"x": viewport_x, "y": viewport_y, "more_info": more_info})
        return confidence
    
    def refine_position_with_history(self, element_name):
        """Refine position with coordinate normalization."""
        for attempt in range(5):
            last_position = self.movement_history[-1] if self.movement_history else None
            prompt_history = "Movement history:\n" + "\n".join(
                [f"Move {i+1}: (x: {pos['x']}, y: {pos['y']}) - Info: {pos['more_info']}" for i, pos in enumerate(self.movement_history)]
            )
            
            # Convert viewport coordinates to screenshot coordinates for the filename
            if last_position:
                screenshot_x, screenshot_y = self.browser.normalize_coordinates(
                    last_position['x'], 
                    last_position['y'], 
                    from_screenshot=False
                )
                zoom_filename = f"images/refine_position_{int(screenshot_x)}_{int(screenshot_y)}.png"
            else:
                zoom_filename = "images/refine_position.png"
            
            self.browser.take_screenshot(zoom_filename)
            
            result = self.qwen2vl.chat(input={
                "query": f"""
You are a mouse controller GPT. Analyze the mouse movement history to refine positioning over the '{element_name}' link. 
Consider each previous move and the accompanying information. 
Provide the response in JSON format with "coordinates" and "more_info".

Example:
{{"coordinates": {{"x": 400, "y": 300}}, "more_info": "Adjusted position based on previous left offset."}}

{prompt_history}
                """,
                "image": zoom_filename
            })

            # Parse the new suggested coordinates from JSON
            try:
                # Handle both list and string results
                if isinstance(result, list):
                    result_str = result[0]
                else:
                    result_str = result
                    
                # Clean up the JSON string
                result_str = result_str.replace('{{{', '{').replace('}}}', '}').strip('[]\'\"')
                
                # Try to extract coordinates using regex if JSON parsing fails
                try:
                    data = json.loads(result_str)
                except json.JSONDecodeError:
                    # Fallback to regex pattern matching
                    coord_pattern = r'"x":\s*(\d+),\s*"y":\s*(\d+)'
                    match = re.search(coord_pattern, result_str)
                    if match:
                        screenshot_x, screenshot_y = map(int, match.groups())
                        data = {
                            "coordinates": {"x": screenshot_x, "y": screenshot_y},
                            "more_info": "Extracted via regex"
                        }
                    else:
                        raise ValueError("Could not extract coordinates")

                # Coordinates from VL model are in screenshot space (1000x1000)
                screenshot_x = int(data["coordinates"]["x"])
                screenshot_y = int(data["coordinates"]["y"])
                # Convert to viewport coordinates
                new_x, new_y = self.browser.normalize_coordinates(screenshot_x, screenshot_y, from_screenshot=True)
                more_info = data.get("more_info", "")
                
                print(f"Successfully parsed coordinates: ({new_x}, {new_y})")
                
            except (ValueError, KeyError) as e:
                print(f"Refinement step failed: Could not extract coordinates. Error: {e}")
                print(f"Raw result: {result}")
                break

            # Update movement history and move the mouse
            self.movement_history.append({"x": new_x, "y": new_y, "more_info": more_info})
            self.browser.move_mouse_to(new_x, new_y)

            # Verify the new position
            confidence = self.verify_mouse_position(new_x, new_y, element_name)
            if confidence >= 90:  # Threshold can be adjusted as needed
                print(f"Position refined and verified at ({new_x}, {new_y}) with confidence {confidence}.")
                return new_x, new_y  # Return refined and verified coordinates

        print("Could not verify position after multiple refinements.")
        return None, None  # Return None if no position verifies after refinements


def click_and_type_element(browser, text_agent, element_name, text_to_type):
    """Click an element and type text into it."""
    helper = MouseControllerHelper(browser, text_agent)
    
    # Locate and click the element
    x, y = helper.locate_element_coordinates(element_name)
    if x is None or y is None:
        print(f"Could not locate '{element_name}' coordinates. Exiting.")
        return False

    # Add the initial position to movement history
    helper.movement_history.append({"x": x, "y": y, "more_info": ""})

    # Move to coordinates and verify
    confidence = helper.verify_mouse_position(x, y, element_name)
    if confidence >= 90:
        browser.click_and_type(x, y, text_to_type)
        browser.take_screenshot(f"images/{element_name}_typed_{x}_{y}.png")
        print(f"Successfully clicked and typed into '{element_name}' at ({x}, {y})")
        return True
    else:
        # Refine position if needed
        refined_x, refined_y = helper.refine_position_with_history(element_name)
        if refined_x is not None and refined_y is not None:
            browser.click_and_type(refined_x, refined_y, text_to_type)
            browser.take_screenshot(f"images/{element_name}_typed_{refined_x}_{refined_y}.png")
            print(f"Successfully clicked and typed after refinement at ({refined_x}, {refined_y})")
            return True
        else:
            print(f"Could not verify and refine position for '{element_name}'. Exiting.")
            return False

def click_element(browser, text_agent, element_name):
    helper = MouseControllerHelper(browser, text_agent)

    # Step 1: Directly locate the element's coordinates
    x, y = helper.locate_element_coordinates(element_name)
    if x is None or y is None:
        print(f"Could not locate '{element_name}' coordinates. Exiting.")
        return

    # Add the initial position to movement history
    helper.movement_history.append({"x": x, "y": y, "more_info": ""})

    # Step 2: Move to the located coordinates and verify
    confidence = helper.verify_mouse_position(x, y, element_name)
    if confidence >= 90:  # Threshold can be adjusted as needed
        new_x, new_y = browser.normalize_coordinates(x,y,from_screenshot=True)
        browser.click_at(x, y)
        browser.take_screenshot(f"images/{element_name}_clicked_{x}_{y}.png")
        print(f"Successfully clicked on '{element_name}' at ({x}, {y}) with confidence {confidence}.")
    else:
        # Step 3: If confidence is low, refine the position incrementally
        print(f"Initial verification confidence ({confidence}) insufficient for '{element_name}' at ({x}, {y}). Refining position.")
        refined_x, refined_y = helper.refine_position_with_history(element_name)

        if refined_x is not None and refined_y is not None:
            browser.click_at(refined_x, refined_y)
            browser.take_screenshot(f"images/{element_name}_clicked_{refined_x}_{refined_y}.png")
            print(f"Successfully clicked on '{element_name}' after refinement at ({refined_x}, {refined_y}).")
        else:
            print(f"Could not verify and refine position for '{element_name}'. Exiting.")

def move_to_element(browser, text_agent, element_name):
    helper = MouseControllerHelper(browser, text_agent)

    # Step 1: Directly locate the element's coordinates
    x, y = helper.locate_element_coordinates(element_name)
    if x is None or y is None:
        print(f"Could not locate '{element_name}' coordinates. Exiting.")
        return

    # Add the initial position to movement history
    helper.movement_history.append({"x": x, "y": y, "more_info": ""})

    # Step 2: Move to the located coordinates and verify
    confidence = helper.verify_mouse_position(x, y, element_name)
    if confidence >= 90:  # Threshold can be adjusted as needed
        browser.click_at(x, y)
        browser.take_screenshot(f"images/{element_name}_clicked_{x}_{y}.png")
        print(f"Successfully clicked on '{element_name}' at ({x}, {y}) with confidence {confidence}.")
    else:
        # Step 3: If confidence is low, refine the position incrementally
        print(f"Initial verification confidence ({confidence}) insufficient for '{element_name}' at ({x}, {y}). Refining position.")
        refined_x, refined_y = helper.refine_position_with_history(element_name)

        if refined_x is not None and refined_y is not None:
            browser.move_mouse_to(refined_x, refined_y)
            browser.take_screenshot(f"images/{element_name}_clicked_{refined_x}_{refined_y}.png")
            print(f"Successfully clicked on '{element_name}' after refinement at ({refined_x}, {refined_y}).")
        else:
            print(f"Could not verify and refine position for '{element_name}'. Exiting.")

def locate_element(browser, text_agent, element_name):
    browser.take_screenshot("images/locate_element.png")
    result = text_agent.chat(input={
        "query": f"Semantically describe the '{element_name}' and spatial location in the image.",
        "image": "images/locate_element.png"
    })
    print(result)
    return result

# Modified usage example
if __name__ == "__main__":
    browser = BrowserController(window_width=1000, window_height=1000)
    qwen2vl = Qwen2VL()
    task_manager = TaskManager(qwen2vl, browser)

    # Define tasks for Discord login
    tasks = [
        Task(
            name="continue_in_browser",
            action="click",
            target="Continue in Browser, small link located below Open App",
            verification="Login textbox is visible"
        ),
        Task(
            name="enter_username",
            action="type",
            target="TEXT BOX located below the email or phone number",
            value=DISCORD_USER,
            verification="Check if username is entered in the text box"
        ),
        Task(
            name="enter_password",
            action="type",
            target="TEXT BOX located below the password field",
            value=DISCORD_PASS,
            verification="Check if password field is visible"
        ),
        Task(
            name="log_in_button",
            action="click",
            target="white text Log in, located inside the blue button",
            verification="Check if Discord dashboard is visible"
        )
    ]

    # Add tasks to manager
    for task in tasks:
        task_manager.add_task(task)

    # Navigate to Discord
    browser.navigate("https://discord.com/channels/@me")
    time.sleep(2)  # Wait for initial page load

    # Run all tasks
    success = task_manager.run_tasks(max_retries=3, delay=2.0)
    
    if success:
        print("All tasks completed successfully!")
        
        # Navigate to specific channel after successful login
        browser.navigate("https://discord.com/channels/999382051935506503/999382052392681605")
        time.sleep(5)
        # Create a new TaskManager instance for the channel tasks
        channel_task_manager = TaskManager(qwen2vl, browser)
        
        join_voice_button_task = Task(
            name="join_voice_button",
            action="click",
            target="white text Join Voice, located inside the green button",
            verification="Joined voice channel"
        )
        
        channel_task_manager.add_task(join_voice_button_task)

        # Run the channel tasks with appropriate delays
        success = channel_task_manager.run_tasks(max_retries=3, delay=5.0)  # Increased delay for page load
        if success:
            print("Successfully clicked green button!")
            time.sleep(600)
        else:
            print("Failed to complete channel tasks")
    else:
        print("Failed to complete login tasks")

    # Cleanup
    browser.close()