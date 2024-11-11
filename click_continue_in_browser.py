from computer.browser import BrowserController
import time
from agents.text import TextAgent
import re

def parse_coordinates(result):
    # Updated regex to extract just the numbers from the response
    match = re.search(r'\(x:\s*(\d+),\s*y:\s*(\d+)\)', result)
    if match:
        return int(match.group(1)), int(match.group(2))
    else:
        return None, None  # Handle case when coordinates are not found

def click_continue_in_browser(browser, text_agent):
    browser.take_screenshot("first_screenshot.png")
    result = text_agent.complete_task(input={"query": "You are a mouse controller GPT. The Dimensions of the screen are 776x464. Locate the Continue in Browser link and reply with the coordinates: (x: <776,y: <464)", "image": "first_screenshot.png"})
    print(result)
    x, y = parse_coordinates(result)
    print(f"Coordinates: ({x}, {y})")
    return x, y

def verify_mouse_over_element(browser, text_agent, x, y):
    browser.move_mouse_to(x, y)
    browser.take_screenshot(f"mouse_moved_{x}_{y}.png")
    result = text_agent.complete_task(input={"query": "You are a mouse controller GPT. Verify that the mouse is over the 'Continue in Browser' link. Reply with 'yes' or 'no' on whether the mouse is over the link.", "image": f"mouse_moved_{x}_{y}.png"})
    print(result)
    return result == "yes"

# Usage example
if __name__ == "__main__":
    browser = BrowserController(window_width=800, window_height=600)
    browser.navigate("https://discord.com/channels/@me")
    text_agent = TextAgent()
    x, y = click_continue_in_browser(browser, text_agent)
    # Move to the element and click if it's found
    if x is not None and y is not None:
        if verify_mouse_over_element(browser, text_agent, x, y):
            browser.click_at(x, y)
            browser.take_screenshot(f"clicked_{x}_{y}.png")
        else:
            print("Mouse is not over the link. Trying again...")
            result = text_agent.complete_task(input={"query": "You are a mouse controller GPT. The Dimensions of the screen are 776x464. The previous mouse move is shown in the image as a red dot.Locate the 'Continue in Browser' button and reply with the coordinates: (x: <776,y: <464)", "image": f"mouse_moved_{x}_{y}.png"})
            x, y = parse_coordinates(result)
            print(f"Coordinates: ({x}, {y})")
            if verify_mouse_over_element(browser, text_agent, x, y):
                browser.click_at(x, y)
                browser.take_screenshot(f"clicked_{x}_{y}.png")
            else:
                print("Mouse is not over the link. Exiting.")
    #if x is None or y is None:
    #    browser.click_at(400, 310)
    # Take a screenshot
    time.sleep(2)
    browser.take_screenshot("continue_in_browser_screenshot.png")

    # Close the browser
    browser.close()