import threading
import time
import logging
import numpy as np
from typing import Tuple, Optional

class Mouse:
    """
    Simulates mouse controls with enhanced position tracking and movement validation.
    """
    def __init__(self, target, screen, movement_speed=1.0):
        self.target = target
        self.screen = screen
        self.movement_speed = movement_speed
        self.current_position = (self.screen.width // 2, self.screen.height // 2)  # Initialize at center
        self.is_clicking = False
        self.last_click = None
        self.position_lock = threading.Lock()
        self.movement_tolerance = 2  # pixels
        
        # Movement constraints
        self.max_speed = 2000  # pixels per second
        self.min_move_time = 0.05  # minimum seconds for any movement
        self.screen_bounds = (screen.width, screen.height)  # Update screen bounds to match the actual screen dimensions
        
        # Initialize logging
        self._setup_logging()

        self.last_position = (self.screen.width // 2, self.screen.height // 2)

        self.active = True  # Flag to control the keep-alive thread
        self.keep_alive_thread = threading.Thread(target=self._keep_alive, daemon=True)
        self.keep_alive_thread.start()

        self.logger.debug(f"Screen dimensions: {self.screen.width}x{self.screen.height}")

        # Add browser reference
        self.browser = target
        
        # Initialize position tracking
        self._position = (screen.width // 2, screen.height // 2)
        self.current_position = self._position

        # Add browser-specific tracking
        self.browser_position = (self.screen.width // 2, self.screen.height // 2)
        self.browser_sync_enabled = True

    def _setup_logging(self):
        """Configure logging for mouse actions"""
        self.logger = logging.getLogger('mouse')
        self.logger.setLevel(logging.DEBUG)
        
        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def move_to(self, x: float, y: float, smooth: bool = True) -> bool:
        """
        Execute mouse movement with improved browser synchronization.
        """
        try:
            # Clamp coordinates to screen bounds
            x = max(0, min(x, self.screen.width))
            y = max(0, min(y, self.screen.height))
            
            start_pos = self.get_position()
            
            if smooth:
                path = self._generate_movement_path(start_pos, (x, y), steps=30)
                for px, py in path:
                    # Update browser position first
                    if self.browser_sync_enabled and hasattr(self.browser, 'move_mouse'):
                        success = self.browser.move_mouse(int(px), int(py))
                        if not success:
                            self.logger.error(f"Browser mouse move failed at ({px}, {py})")
                            return False
                    
                    # Then update internal position
                    with self.position_lock:
                        self._position = (px, py)
                        self.current_position = (px, py)
                        self.browser_position = (px, py)
                        
                    time.sleep(0.01 / self.movement_speed)
            else:
                # Direct movement
                if self.browser_sync_enabled and hasattr(self.browser, 'move_mouse'):
                    success = self.browser.move_mouse(int(x), int(y))
                    if not success:
                        return False
                
                with self.position_lock:
                    self._position = (x, y)
                    self.current_position = (x, y)
                    self.browser_position = (x, y)

            return True

        except Exception as e:
            self.logger.error(f"Error moving mouse: {e}")
            return False

    def _generate_movement_path(
        self, 
        start: Tuple[float, float], 
        end: Tuple[float, float],
        steps: int = 30
    ) -> list:
        """
        Generate smooth movement path using improved easing.
        """
        path = []
        for i in range(steps + 1):
            t = i / steps
            # Improved easing function for more natural movement
            t = t * t * (3 - 2 * t)  # Smoothstep interpolation
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            path.append((x, y))
        return path

    def _validate_coordinates(self, x: float, y: float) -> bool:
        """
        Validate coordinates are within viewport bounds.
        """
        return (0 <= x <= self.screen_bounds[0] and 
                0 <= y <= self.screen_bounds[1])

    def _update_position(self, x: float, y: float):
        """Thread-safe position update."""
        with self.position_lock:
            self.current_position = (y, x)
            # Update target's mouse position if method exists
            if hasattr(self.target, 'update_mouse_position'):
                self.target.update_mouse_position(
                    type('Event', (), {'x': y, 'y': x})
                )

    @property
    def position(self) -> Tuple[float, float]:
        """Thread-safe position access."""
        with self.position_lock:
            return self.current_position

    def get_position(self) -> Tuple[float, float]:
        """
        Get current mouse position with browser sync.
        """
        with self.position_lock:
            if self.browser_sync_enabled and hasattr(self.browser, 'get_mouse_position'):
                browser_pos = self.browser.get_mouse_position()
                if browser_pos:
                    self.browser_position = browser_pos
                    self._position = browser_pos
                    self.current_position = browser_pos
            return self._position

    def click(self, button: str = 'left', double: bool = False) -> bool:
        """
        Enhanced click with browser synchronization.
        """
        try:
            # Ensure browser position is synced before clicking
            if self.browser_sync_enabled:
                current_pos = self.get_position()
                if hasattr(self.browser, 'move_mouse'):
                    self.browser.move_mouse(*current_pos)
                
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
        Additional initialization if needed.
        """
        # Ensure the mouse starts at the center of the screen
        center_x = self.screen.width // 2
        center_y = self.screen.height // 2
        self.move_to(center_x, center_y, smooth=False)
        self.logger.info(f"Mouse initialized at center: ({center_x}, {center_y})")

    def _keep_alive(self):
        """Background thread to ensure mouse remains active."""
        while self.active:
            try:
                # Perform a lightweight action to keep the mouse active
                self.target.move_mouse(*self.current_position)
                time.sleep(30)  # Interval can be adjusted as needed
            except Exception as e:
                self.logger.error(f"Keep-alive failed: {e}")
                # Optionally, implement reinitialization logic here

    def stop(self):
        """Stop the mouse and its keep-alive thread."""
        self.active = False
        self.keep_alive_thread.join()
