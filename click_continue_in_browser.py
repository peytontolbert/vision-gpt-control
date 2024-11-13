from computer.browser import BrowserController
import time
from agents.text import TextAgent
import re
import json


class MouseControllerHelper:
    def __init__(self, browser, text_agent):
        self.browser = browser
        self.text_agent = text_agent
        self.movement_history = []  # Track movement history for adaptive refinement

    def parse_coordinates(self, result):
        """Parse the last successful coordinates from the TextAgent result."""
        # Find all coordinate matches in the result text
        matches = re.findall(r'\(x:\s*(\d+),\s*y:\s*(\d+)\)', result)
        
        # If multiple coordinates are found, use only the last one
        if matches:
            last_match = matches[-1]
            return int(last_match[0]), int(last_match[1])
        else:
            return None, None  # Return None if no coordinates are found

    def locate_element_coordinates(self, element_name):
        """Ask the TextAgent to locate the precise coordinates of an element."""
        self.browser.take_screenshot("images/element_screenshot.png")
        result = self.text_agent.complete_task(input={
            "query": f"You are a mouse controller GPT. The screen dimensions are 776x464. Locate the exact center of the '{element_name}' link and reply with the exact coordinates as (x: <776, y: <464).",
            "image": "images/element_screenshot.png"
        })
        x, y = self.parse_coordinates(result)
        print(f"Located coordinates for '{element_name}': ({x}, {y})")
        return x, y

    def verify_mouse_position(self, x, y, element_name):
        """Verify if the mouse is positioned over the specified element with confidence scoring and additional information."""
        self.browser.move_mouse_to(x, y)
        self.browser.take_screenshot(f"images/mouse_position_{x}_{y}.png")
        result = self.text_agent.complete_task(input={
            "query": f"""
Verify how precisely the mouse is over the '{element_name}' link. 
Reply with a JSON object containing:
- "confidence": a score between 0 and 100,
- "more_info": additional information about the verification.
Example:
{{"confidence": 85, "more_info": "Mouse is slightly to the left of the target."}}
            """,
            "image": f"images/mouse_position_{x}_{y}.png"
        })
        print(f"Verification result: {result}")
        try:
            data = json.loads(result.strip())
            confidence = float(data.get("confidence", 0.0))
            more_info = data.get("more_info", "")
            # Include more_info in movement history for clearer instructions
            self.movement_history.append({"x": x, "y": y, "more_info": more_info})
        except (ValueError, json.JSONDecodeError):
            confidence = 0.0  # Default to 0 if parsing fails
            more_info = "Invalid response format."
            self.movement_history.append({"x": x, "y": y, "more_info": more_info})
        return confidence
    
    def refine_position_with_history(self, element_name):
        """Refine the mouse position using movement history and step-by-step guidance."""
        for attempt in range(5):  # Limit to 5 refinements to prevent infinite loops
            last_position = self.movement_history[-1] if self.movement_history else None
            prompt_history = "Movement history:\n" + "\n".join(
                [f"Move {i+1}: (x: {pos['x']}, y: {pos['y']}) - Info: {pos['more_info']}" for i, pos in enumerate(self.movement_history)]
            )
            
            self.browser.take_screenshot(f"images/refine_position_{last_position['x']}_{last_position['y']}.png")
            result = self.text_agent.complete_task(input={
                "query": f"""
You are a mouse controller GPT. Analyze the mouse movement history to refine positioning over the '{element_name}' link. 
Consider each previous move and the accompanying information. 
Suggest the next precise step to hover directly over the link. 
Provide the response in JSON format with "coordinates" and "more_info".

Example:
{{{{"coordinates": {{"x": 400, "y": 300}}, "more_info": "Adjusted position based on previous left offset."}}}}

{prompt_history}
                """,
                "image": f"images/refine_position_{last_position['x']}_{last_position['y']}.png"
            })

            # Parse the new suggested coordinates from JSON
            try:
                data = json.loads(result.strip())
                new_x = int(data["coordinates"]["x"])
                new_y = int(data["coordinates"]["y"])
                more_info = data.get("more_info", "")
            except (ValueError, KeyError, json.JSONDecodeError):
                print("Refinement step failed: invalid JSON response.")
                break  # Exit if no valid refinement is provided

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

# Usage example
if __name__ == "__main__":
    browser = BrowserController(window_width=800, window_height=600)
    browser.navigate("https://discord.com/channels/@me")
    text_agent = TextAgent()

    click_element(browser, text_agent, "Continue in Browser")

    #if x is None or y is None:
    #    browser.click_at(400, 310)
    # Take a screenshot
    time.sleep(2)
    browser.take_screenshot("images/continue_in_browser_screenshot.png")

    # Close the browser
    browser.close()