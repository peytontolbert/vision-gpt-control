from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
from PIL import Image, ImageDraw, ImageFont
import os

class BrowserController:
    def __init__(self, window_width=1000, window_height=1000):
        # Configure Edge WebDriver
        edge_options = Options()
        edge_options.add_argument(f"--window-size={window_width},{window_height}")
        self.driver = webdriver.Edge(options=edge_options)
        
        # Wait for the browser to open
        time.sleep(2)
        
        # Get the actual window dimensions (for accurate mouse movements)
        self.window_width = self.driver.execute_script("return window.innerWidth")
        self.window_height = self.driver.execute_script("return window.innerHeight")
        self.actions = ActionChains(self.driver)
        self.last_mouse_position = None  # Initialize mouse position tracking
        
        print(f"Initialized browser with dimensions: {self.window_width}x{self.window_height}")

    def navigate(self, url):
        """Navigate to a specified URL."""
        self.driver.get(url)
        print(f"Navigated to {url}")
        time.sleep(2)  # Wait for the page to load

    def locate_element_by_text(self, text):
        """Locate an element by link text and return its center coordinates."""
        try:
            element = self.driver.find_element(By.LINK_TEXT, text)
            location = element.location
            size = element.size
            # Calculate center coordinates within the browser
            center_x = location['x'] + (size['width'] / 2)
            center_y = location['y'] + (size['height'] / 2)
            print(f"Located element '{text}' at ({center_x}, {center_y})")
            return center_x, center_y
        except Exception as e:
            print(f"Error locating element by text '{text}': {e}")
            return None, None

    def move_mouse_to(self, x, y):
        """Move the virtual mouse to the specified coordinates within the browser."""
        print(f" window dimensions: {self.window_width}x{self.window_height}")
        print(f" last mouse position: {self.last_mouse_position}")
        if self.last_mouse_position is None:
            # If this is the first movement, set the initial position as the current (0, 0)
            self.last_mouse_position = (0, 0)
        if 0 <= x <= self.window_width and 0 <= y <= self.window_height:
            # Move to the coordinates within the browser window
            offset_x = x - self.last_mouse_position[0]
            offset_y = y - self.last_mouse_position[1]
            self.actions.move_by_offset(offset_x, offset_y).perform()
            self.last_mouse_position = (x, y)
            self.take_screenshot(f"images/screenshot_{x}_{y}.png")
            print(f"Moved mouse to ({x}, {y}) within the browser window.")
            self.last_mouse_position = (x, y)  # Update mouse position
        else:
            print(f"Coordinates ({x}, {y}) are out of browser bounds.")

    def click_at(self, x, y):
        """Move the virtual mouse to (x, y) and perform a click."""
        self.move_mouse_to(x, y)
        self.actions.click().perform()
        print(f"Clicked at ({x}, {y}) within the browser window.")

    def take_screenshot(self, filename="images/screenshot.png"):
        """Take a screenshot of the browser, save it, and overlay an enhanced coordinate system with a mouse position."""
        # Take a screenshot using WebDriver
        self.driver.save_screenshot(filename)
        print(f"Screenshot saved as {filename}")

        try:
            # Open the screenshot and prepare for drawing
            image = Image.open(filename)
            draw = ImageDraw.Draw(image)

            # Set up parameters for overlay
            grid_spacing = 50  # Distance in pixels between each grid line
            quadrant_color = (0, 200, 0)  # Color for quadrant labels
            grid_color = (150, 150, 150)  # Light gray color for grid lines
            radial_color = (0, 100, 255)  # Blue for radial distance markers
            text_color = "black"
            
            # Load a font for better readability (optional)
            try:
                font = ImageFont.truetype("arial.ttf", 15)
            except IOError:
                font = None  # Fall back to default if the font is not available

            # Draw vertical and horizontal grid lines
            for x in range(0, self.window_width, grid_spacing):
                draw.line((x, 0, x, self.window_height), fill=grid_color, width=1)
                # Label x-axis coordinates
                label = f"{x}"
                draw.text((x + 2, 2), label, fill=text_color, font=font)

            for y in range(0, self.window_height, grid_spacing):
                draw.line((0, y, self.window_width, y), fill=grid_color, width=1)
                # Label y-axis coordinates
                label = f"{y}"
                draw.text((2, y + 2), label, fill=text_color, font=font)

            # Overlay the mouse position if available
            if self.last_mouse_position:
                mouse_x, mouse_y = self.last_mouse_position
                mouse_size = 10  # Size of the mouse cursor overlay
                # Draw a red circle at the mouse position
                draw.ellipse(
                    (mouse_x - mouse_size, mouse_y - mouse_size, mouse_x + mouse_size, mouse_y + mouse_size),
                    fill='red',
                    outline='black'
                )
                # Label the mouse position with coordinates
                draw.text((mouse_x + 15, mouse_y), f"({mouse_x}, {mouse_y})", fill="red", font=font)
                print(f"Mouse overlay added at ({mouse_x}, {mouse_y})")

            # Save the image with the enhanced overlay
            image.save(filename)
            print(f"Enhanced coordinate grid, radial markers, quadrants, and mouse overlay added to {filename}")
        except Exception as e:
            print(f"Error overlaying enhanced coordinate system on screenshot: {e}")
            
    def close(self):
        """Close the browser."""
        self.driver.quit()
        print("Browser closed.")

