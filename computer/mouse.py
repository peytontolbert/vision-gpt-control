import threading
import time
import logging
from typing import Tuple, Optional
from selenium.webdriver.common.action_chains import ActionChains

class Mouse:
    """
    Simulates mouse controls with position tracking and movement validation.
    """
    def __init__(self, browser, screen, movement_speed=1.0):
        self.browser = browser
        self.screen = screen
        self.movement_speed = movement_speed
        self._position = (0, 0)
        self.logger = logging.getLogger(__name__)
        self.position_lock = threading.Lock()
        self.browser_sync_enabled = True

    def scale_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Scale screen coordinates to browser viewport coordinates."""
        viewport_width, viewport_height = self.browser.get_viewport_size()
        screen_width, screen_height = self.screen.get_resolution()
        
        # Scale coordinates proportionally
        scaled_x = int((x / screen_width) * viewport_width)
        scaled_y = int((y / screen_height) * viewport_height)
        
        return (scaled_x, scaled_y)

    def move_to(self, x: int, y: int, smooth=True) -> bool:
        """Move mouse to coordinates, scaling them to viewport size."""
        try:
            # Get viewport dimensions first
            viewport_width, viewport_height = self.browser.get_viewport_size()
            if not viewport_width or not viewport_height:
                self.logger.error("Could not get viewport dimensions")
                return False
                
            # Get screen dimensions
            screen_width, screen_height = self.screen.get_resolution()
            
            # Calculate scaling factors
            scale_x = viewport_width / screen_width
            scale_y = viewport_height / screen_height
            
            # Scale coordinates to viewport and ensure they're within bounds
            viewport_x = min(max(0, int(x * scale_x)), viewport_width - 1)
            viewport_y = min(max(0, int(y * scale_y)), viewport_height - 1)
            
            # Use browser's webdriver to execute mouse movement
            if hasattr(self.browser, 'webdriver') and self.browser.webdriver:
                script = f"""
                    window.scrollTo(0, 0);  // Reset scroll position
                    const event = new MouseEvent('mousemove', {{
                        clientX: {viewport_x},
                        clientY: {viewport_y},
                        bubbles: true
                    }});
                    document.elementFromPoint({viewport_x}, {viewport_y})?.dispatchEvent(event);
                """
                self.browser.webdriver.execute_script(script)
                
                # Update internal position
                with self.position_lock:
                    self._position = (x, y)
                
                # Verify position
                actual_pos = self.get_position()
                tolerance = 5
                if (abs(actual_pos[0] - x) <= tolerance and 
                    abs(actual_pos[1] - y) <= tolerance):
                    return True
                    
                self.logger.warning(f"Position verification failed. Expected: ({x}, {y}), Got: {actual_pos}")
                return False
                
            self.logger.error("Browser webdriver not available")
            return False
                
        except Exception as e:
            self.logger.error(f"Mouse movement failed: {e}")
            return False

    @property
    def position(self) -> Tuple[float, float]:
        """Thread-safe position access."""
        with self.position_lock:
            return self._position

    def get_position(self) -> Tuple[float, float]:
        """Get current mouse position with browser sync."""
        try:
            with self.position_lock:
                if self.browser_sync_enabled:
                    # Get browser viewport coordinates
                    viewport_pos = self.browser.get_mouse_position()
                    if viewport_pos:
                        viewport_x, viewport_y = viewport_pos
                        
                        # Get scroll position
                        scroll_x, scroll_y = self.browser.get_scroll_position()
                        
                        # Adjust for scroll position
                        actual_x = viewport_x - scroll_x
                        actual_y = viewport_y - scroll_y
                        
                        # Scale back to screen coordinates
                        scale_x = self.screen.width / self.browser.get_viewport_size()[0]
                        scale_y = self.screen.height / self.browser.get_viewport_size()[1]
                        
                        screen_x = int(actual_x * scale_x)
                        screen_y = int(actual_y * scale_y)
                        
                        self._position = (screen_x, screen_y)
                        return self._position
                return self._position
        except Exception as e:
            self.logger.error(f"Error getting mouse position: {e}")
            return self._position

    def click(self, button: str = 'left', double: bool = False) -> bool:
        """
        Execute mouse click.
        """
        try:
            # Execute click through browser
            if hasattr(self.browser, 'click_mouse'):
                success = self.browser.click_mouse(button)
                if not success:
                    self.logger.error("Browser click failed")
                    return False
                
                if double:
                    time.sleep(0.1)
                    success = self.browser.click_mouse(button)
                    if not success:
                        return False

            self.logger.debug(
                f"{'Double ' if double else ''}Click executed at {self.get_position()}"
            )
            return True
                
        except Exception as e:
            self.logger.error(f"Error executing click: {e}")
            return False

    def initialize(self):
        """
        Initialize mouse position to center of screen.
        """
        center_x = self.screen.width // 2
        center_y = self.screen.height // 2
        self.move_to(center_x, center_y, smooth=False)
        self.logger.info(f"Mouse initialized at center: ({center_x}, {center_y})")
