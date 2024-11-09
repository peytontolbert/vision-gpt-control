import logging
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from PIL import Image
import io
import threading
import time
from typing import Tuple, Optional

class Browser:
    """
    A class to handle Selenium browser operations including mouse, keyboard, and viewport management.
    """
    
    def __init__(self, headless: bool = True, window_size: Tuple[int, int] = (800, 600)):
        self.webdriver: Optional[webdriver.Edge] = None
        self.actions: Optional[ActionChains] = None
        self.wait: Optional[WebDriverWait] = None
        self._window_size = window_size
        self._headless = headless
        self._default_timeout = 10
        
        # Screen capture settings
        self.is_capturing = False
        self.capture_thread = None
        self.current_frame = None
        self.target_fps = 30
        
        # Mouse position tracking
        self._mouse_position = (0, 0)
        self._mouse_position_lock = threading.Lock()
        
        self.logger = logging.getLogger(__name__)

    def launch(self) -> bool:
        """Launches the browser with configured options."""
        try:
            options = Options()
            options.use_chromium = True
            options.add_argument("--no-sandbox")
            options.add_argument(f"--window-size={self._window_size[0]},{self._window_size[1]}")
            options.add_argument("--disable-dev-shm-usage")
            options.headless = self._headless
            
            self.webdriver = webdriver.Edge(options=options)
            self.actions = ActionChains(self.webdriver)
            self.wait = WebDriverWait(self.webdriver, self._default_timeout)
            
            # Start screen capture
            self.is_capturing = True
            self._start_screen_capture()
            
            self.logger.info("Browser launched successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to launch browser: {e}")
            self.close()
            return False

    def _start_screen_capture(self):
        """Starts the screen capture thread."""
        def capture_loop():
            frame_interval = 1.0 / self.target_fps
            
            while self.is_capturing:
                try:
                    if not self.webdriver:
                        break
                        
                    screenshot = self.webdriver.get_screenshot_as_png()
                    self.current_frame = Image.open(io.BytesIO(screenshot)).convert('RGB')
                    time.sleep(frame_interval)
                    
                except Exception as e:
                    self.logger.error(f"Screen capture error: {e}")
                    time.sleep(0.1)
            
        self.capture_thread = threading.Thread(target=capture_loop, daemon=True)
        self.capture_thread.start()

    # Navigation methods
    def navigate(self, url: str) -> bool:
        """Navigates to the specified URL."""
        try:
            self.webdriver.get(url)
            return True
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            return False

    def wait_until_loaded(self, timeout: Optional[int] = None) -> bool:
        """Waits for page to finish loading."""
        try:
            timeout = timeout or self._default_timeout
            self.wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
            return True
        except TimeoutException:
            return False

    # Mouse control methods
    def move_mouse(self, x: int, y: int) -> bool:
        """Moves mouse to specified coordinates."""
        try:
            current_x, current_y = self._mouse_position
            delta_x = x - current_x
            delta_y = y - current_y
            
            self.actions.move_by_offset(delta_x, delta_y).perform()
            
            with self._mouse_position_lock:
                self._mouse_position = (x, y)
            
            self.actions = ActionChains(self.webdriver)  # Reset actions
            return True
            
        except Exception as e:
            self.logger.error(f"Mouse movement failed: {e}")
            return False

    def click_mouse(self, button: str = 'left') -> bool:
        """Performs mouse click."""
        try:
            if button == 'left':
                self.actions.click()
            elif button == 'right':
                self.actions.context_click()
            elif button == 'middle':
                self.actions.middle_click()
            else:
                return False
                
            self.actions.perform()
            return True
            
        except Exception as e:
            self.logger.error(f"Mouse click failed: {e}")
            return False

    # Keyboard control methods
    def type_text(self, text: str) -> bool:
        """Types the specified text."""
        try:
            self.actions.send_keys(text).perform()
            return True
        except Exception as e:
            self.logger.error(f"Text input failed: {e}")
            return False

    def press_key(self, key: str) -> bool:
        """Presses the specified key."""
        try:
            self.actions.key_down(key).perform()
            return True
        except Exception as e:
            self.logger.error(f"Key press failed: {e}")
            return False

    def release_key(self, key: str) -> bool:
        """Releases the specified key."""
        try:
            self.actions.key_up(key).perform()
            return True
        except Exception as e:
            self.logger.error(f"Key release failed: {e}")
            return False

    # Element interaction methods
    def find_element(self, selector: str, timeout: Optional[int] = None):
        """Finds element using CSS selector."""
        try:
            timeout = timeout or self._default_timeout
            return self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except Exception:
            return None

    def is_field_active(self, field_id: str) -> bool:
        """Checks if input field is active."""
        try:
            return self.webdriver.execute_script(
                f"return document.activeElement.id === '{field_id}';"
            )
        except Exception as e:
            self.logger.error(f"Field check failed: {e}")
            return False

    # Viewport methods
    def get_window_rect(self) -> Tuple[int, int, int, int]:
        """Returns the browser window rectangle."""
        try:
            size = self.webdriver.get_window_size()
            pos = self.webdriver.get_window_position()
            return (pos['x'], pos['y'], size['width'], size['height'])
        except Exception:
            return (0, 0, self._window_size[0], self._window_size[1])

    def get_current_frame(self) -> Optional[Image.Image]:
        """Returns the current browser frame."""
        return self.current_frame

    def close(self):
        """Closes the browser and cleanup resources."""
        self.is_capturing = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        if self.webdriver:
            try:
                self.webdriver.quit()
            except Exception as e:
                self.logger.error(f"Browser close failed: {e}")
