import threading
import time
import logging

class Keyboard:
    """
    Simulates keyboard controls with enhanced key press handling.
    """
    def __init__(self, target, screen):
        self.target = target
        self.screen = screen
        self.current_keys = set()
        self.position_lock = threading.Lock()
        self.logger = logging.getLogger('keyboard')
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize logging handlers if not present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
        # Removed queue and threading attributes
        # self.action_queue = []
        # self.queue_lock = threading.Lock()
        # self.running = False
        # self.thread = None
    
    def press_key(self, key: str) -> bool:
        """
        Press a key directly without queueing.
        
        Args:
            key: The key to press
            
        Returns:
            bool: True if key press was successful
        """
        try:
            self.target.press_key(key)
            self.logger.debug(f"Key pressed: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Error pressing key '{key}': {e}")
            return False
    
    def release_key(self, key: str) -> bool:
        """
        Release a key directly without queueing.
        
        Args:
            key: The key to release
            
        Returns:
            bool: True if key release was successful
        """
        try:
            self.target.release_key(key)
            self.logger.debug(f"Key released: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Error releasing key '{key}': {e}")
            return False
    
    def type_text(self, text: str) -> bool:
        """
        Types the given text using the keyboard.
        
        Args:
            text (str): The text to type.
        
        Returns:
            bool: True if typing was successful, False otherwise.
        """
        try:
            for char in text:
                self.press_key(char)
                self.release_key(char)
                time.sleep(0.05)  # Slight delay between key presses for reliability
            self.logger.debug(f"Typed text: {text}")
            return True
        except Exception as e:
            self.logger.error(f"Error typing text '{text}': {e}")
            return False
