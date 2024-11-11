import logging
import numpy as np
from PIL import Image
import pyautogui
import time
import threading
from typing import Tuple, Optional
import io

class Screen:
    """A simplified screen class focused on capturing Discord viewport screenshots."""
    
    def __init__(self, browser):
        self.browser = browser
        self.browser_sync_enabled = True
        # Initialize with default size, will be updated in initialize()
        viewport_width, viewport_height = self.browser.get_viewport_size()
        self.width, self.height = viewport_width, viewport_height
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.last_frame_time = time.time()

    def initialize(self):
        """Initialize the screen capture system."""
        try:
            # Get viewport dimensions from browser
            if self.browser and self.browser.webdriver:
                self.width, self.height = self.browser.get_viewport_size()
                logging.info(f"Screen initialized with viewport size: {self.width}x{self.height}")
            else:
                logging.warning("Browser not available, using default dimensions")
                
            # Capture initial screen state
            self.current_frame = self.capture()
            logging.info("Screen initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing screen: {e}")
            raise

    def capture(self) -> Optional[Image.Image]:
        """
        Capture current screen state, prioritizing browser frame if available.
        
        Returns:
            Image.Image: The captured screen frame
            None: If capture fails
        """
        try:
            # Try to get browser frame first if enabled
            if self.browser_sync_enabled and self.browser:
                browser_frame = self.browser.get_current_frame()
                if browser_frame:
                    self.current_frame = browser_frame
                    return browser_frame

            # Fallback to screenshot
            screenshot = pyautogui.screenshot()
            self.current_frame = screenshot
            return screenshot

        except Exception as e:
            logging.error(f"Error capturing screen state: {e}", exc_info=True)
            return None

    def get_current_frame(self) -> Optional[Image.Image]:
        """
        Returns the most recent frame.
        """
        try:
            if not self.current_frame:
                return Image.new('RGB', (self.width, self.height), 'black')
            return self.current_frame
        except Exception as e:
            logging.error(f"Error getting current frame: {e}")
            return None

    def get_screen_image(self) -> Optional[np.ndarray]:
        """
        Returns the current screen image as a numpy array, scaled to match viewport dimensions.
        """
        try:
            # Get PNG bytes from webdriver
            png_bytes = self.browser.webdriver.get_screenshot_as_png()
            if png_bytes is None:
                logging.warning("No current frame available")
                return None
                
            # Convert PNG bytes to PIL Image
            image = Image.open(io.BytesIO(png_bytes))
            
            # Get viewport dimensions
            viewport_width, viewport_height = self.get_resolution()
            
            # Resize image to match viewport dimensions
            image = image.resize((viewport_width, viewport_height))
            
            # Convert PIL Image to numpy array
            return np.array(image)
            
        except Exception as e:
            logging.error(f"Error getting screen image: {e}")
            return None

    def get_resolution(self) -> Tuple[int, int]:
        """
        Get the screen resolution.

        Returns:
            Tuple[int, int]: Width and height of the viewport in pixels.
        """
        try:
            if self.browser and self.browser.webdriver:
                viewport_size = self.browser.get_viewport_size()
                self.width, self.height = viewport_size  # Update internal dimensions
                logging.debug(f"Viewport size: {viewport_size}")
                return viewport_size
            return (self.width, self.height)
        except Exception as e:
            logging.error(f"Error retrieving screen resolution: {e}")
            return (776, 464)  # Use actual viewport size as fallback
