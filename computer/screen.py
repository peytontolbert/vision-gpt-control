import logging
import tkinter as tk
import os
from PIL import Image, ImageTk
import numpy as np
import time
import cv2
import threading
from typing import Tuple
import pyautogui

class Screen:
    def __init__(self):
        self.width, self.height = pyautogui.size()
        self.current_state = None
        self.ui_elements = []
        self.window = None
        self.canvas = None
        self.current_frame = None
        self.mouse_position = (self.width // 2, self.height // 2)  # Initialize at center
        self.is_container = os.getenv("IS_CONTAINER", "False") == "True"
        self.frame_buffer = []
        self.frame_lock = threading.Lock()  # Add thread safety
        self.last_frame_time = time.time()  # Initialize to current time
        self.frame_count = 0
        self.fps = 0
        self._tk_ready = False
        self.browser_frame = None
        self.browser_frame_timestamp = 0
        self.browser_sync_enabled = True

    def initialize(self):
        """
        Initializes the simulated screen with improved container support.
        """
        try:
            if not self.is_container:
                if not self._tk_ready:
                    self.window = tk.Tk()
                    self.window.title("Bob's View")
                    self.window.geometry(f"{self.width}x{self.height}")
                    
                    # Create canvas for drawing
                    self.canvas = tk.Canvas(
                        self.window, 
                        width=self.width, 
                        height=self.height
                    )
                    self.canvas.pack()
                    
                    # Bind mouse movement
                    self.canvas.bind('<Motion>', self.update_mouse_position)
                    
                    self._tk_ready = True
                    
                    # Start Tk event loop in the main thread
                    self.window.after(0, self._run_tk_loop)
            
            logging.debug("Screen initialized in %s mode", 
                         "container" if self.is_container else "window")

            # Position mouse at center if not in container
            if not self.is_container:
                self.update_mouse_position_event((self.width // 2, self.height // 2))
                logging.info(f"Mouse positioned at center: ({self.width // 2}, {self.height // 2})")
            
            self.current_state = self.capture()
            
        except Exception as e:
            logging.error(f"Error initializing screen: {e}")
            raise

    def _run_tk_loop(self):
        """Run Tkinter event loop"""
        try:
            self.window.mainloop()
        except Exception as e:
            logging.error(f"Error in Tk event loop: {e}")

    def update_mouse_position(self, event):
        """
        Updates the current mouse position.
        """
        self.mouse_position = (event.x, event.y)
        logging.debug(f"Mouse position updated to {self.mouse_position}")

    def get_mouse_position(self):
        """
        Returns the current mouse position.
        """
        return self.mouse_position

    def update_frame(self, frame):
        """
        Updates the current frame with browser integration.
        """
        try:
            with self.frame_lock:
                current_time = time.time()
                
                # Handle browser frame if available
                if self.browser_sync_enabled and hasattr(self.browser, 'get_current_frame'):
                    browser_frame = self.browser.get_current_frame()
                    if browser_frame:
                        self.browser_frame = browser_frame
                        self.browser_frame_timestamp = current_time
                        frame = browser_frame  # Use browser frame instead
                
                # Continue with normal frame processing
                if frame is None:
                    logging.warning("Received None frame")
                    return
                    
                if isinstance(frame, np.ndarray):
                    frame = self._process_numpy_frame(frame)
                elif not isinstance(frame, Image.Image):
                    raise ValueError(f"Unsupported frame type: {type(frame)}")

                # Update current frame and buffer
                self.current_frame = frame
                self._update_frame_buffer(frame)
                
                # Update display if needed
                if not self.is_container and self.canvas and self._tk_ready:
                    try:
                        photo = ImageTk.PhotoImage(frame)
                        self.canvas.after(0, lambda: self._update_canvas(photo))
                    except Exception as e:
                        logging.error(f"Error updating canvas: {e}")

        except Exception as e:
            logging.error(f"Error updating frame: {e}", exc_info=True)

    def _process_numpy_frame(self, frame):
        """Process numpy array frames to correct format"""
        if len(frame.shape) == 2:  # Grayscale
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:  # RGBA
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
        elif frame.shape[2] == 3 and frame.dtype == np.uint8:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame)

    def _update_frame_buffer(self, frame):
        """Update frame buffer with timestamp and maintain size"""
        self.frame_buffer.append({
            'frame': frame,
            'timestamp': time.time()
        })
        
        # Keep last 3 seconds of frames (assuming 30 FPS)
        while len(self.frame_buffer) > 90:
            self.frame_buffer.pop(0)

    def get_current_frame(self):
        """
        Returns current frame with browser priority.
        """
        try:
            # First try to get browser frame if enabled
            if self.browser_sync_enabled and self.browser_frame:
                if time.time() - self.browser_frame_timestamp < 1.0:  # Use if less than 1 second old
                    return self.browser_frame
            
            # Fall back to normal frame handling
            if not self.current_frame:
                return Image.new('RGB', (self.width, self.height), 'black')
                
            return self.current_frame
            
        except Exception as e:
            logging.error(f"Error getting current frame: {e}")
            return None

    def get_frame_buffer(self):
        """
        Returns the recent frame history buffer.
        
        Returns:
            list: List of recent frames, each as PIL Image
        """
        try:
            return [
                Image.fromarray(frame) if isinstance(frame, np.ndarray) else frame 
                for frame in self.frame_buffer
            ]
        except Exception as e:
            logging.error(f"Error getting frame buffer: {e}")
            return []

    def capture(self):
        """
        Captures current screen state with enhanced metadata, quality control and error handling.
        
        Returns:
            dict: Screen state including timestamp, resolution, UI elements, and quality metrics
            None: If capture fails
        """
        try:
            # First try to get current frame with error handling
            current_frame = self.get_current_frame()
            if current_frame is None:
                # Try to create a blank frame as fallback
                current_frame = Image.new('RGB', (self.width, self.height), 'black')
                logging.warning("Created blank frame as fallback after capture failure")
                
            # Enhanced screen state with quality metrics
            screen_state = {
                'timestamp': time.time(),
                'resolution': (self.width, self.height),
                'ui_elements': self.ui_elements.copy(),
                'frame': current_frame,
                'mouse_position': self.mouse_position,
                'quality_metrics': {
                    'brightness': self._calculate_brightness(current_frame),
                    'contrast': self._calculate_contrast(current_frame),
                    'sharpness': self._calculate_sharpness(current_frame)
                }
            }
            
            # Add frame to buffer with quality check
            if self._check_frame_quality(current_frame):
                self.frame_buffer.append({
                    'frame': current_frame,
                    'timestamp': time.time(),
                    'metadata': screen_state
                })
                
                # Maintain buffer size
                while len(self.frame_buffer) > 100:
                    self.frame_buffer.pop(0)
                    
            return screen_state
            
        except Exception as e:
            logging.error(f"Error capturing screen state: {e}", exc_info=True)
            return None

    def _calculate_brightness(self, frame):
        """Calculate average brightness of frame."""
        try:
            if isinstance(frame, Image.Image):
                frame = np.array(frame)
            return np.mean(frame)
        except Exception as e:
            logging.error(f"Error calculating brightness: {e}")
            return 0

    def _calculate_contrast(self, frame):
        """Calculate RMS contrast of frame."""
        try:
            if isinstance(frame, Image.Image):
                frame = np.array(frame)
            return np.std(frame)
        except Exception as e:
            logging.error(f"Error calculating contrast: {e}")
            return 0

    def _calculate_sharpness(self, frame):
        """Calculate image sharpness using Laplacian variance."""
        try:
            if isinstance(frame, Image.Image):
                frame = np.array(frame)
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            return cv2.Laplacian(frame, cv2.CV_64F).var()
        except Exception as e:
            logging.error(f"Error calculating sharpness: {e}")
            return 0

    def _check_frame_quality(self, frame, min_brightness=10, min_contrast=5, min_sharpness=100):
        """
        Check if frame meets minimum quality requirements.
        """
        try:
            brightness = self._calculate_brightness(frame)
            contrast = self._calculate_contrast(frame)
            sharpness = self._calculate_sharpness(frame)
            
            return (brightness >= min_brightness and 
                    contrast >= min_contrast and 
                    sharpness >= min_sharpness)
        except Exception as e:
            logging.error(f"Error checking frame quality: {e}")
            return False

    def display_elements(self, elements):
        """Update UI elements on screen"""
        self.ui_elements = elements

    def _update_canvas(self, photo):
        """Thread-safe method to update canvas"""
        if not self.canvas:
            return
        
        try:
            # Store reference to photo to prevent garbage collection
            if not hasattr(self, '_current_photo'):
                self._current_photo = None
                
            self._current_photo = photo  # Keep strong reference
            
            def update():
                try:
                    if self.canvas.winfo_exists():
                        self.canvas.delete("all")
                        self.canvas.create_image(0, 0, image=self._current_photo, anchor='nw')
                except Exception as e:
                    logging.error(f"Error in canvas update: {e}")
                    
            # Schedule update in main thread
            if self.window and self.window.winfo_exists():
                self.window.after(0, update)
                
        except Exception as e:
            logging.error(f"Error preparing canvas update: {e}")

    def get_screen_image(self):
        """
        Returns the current screen image as a numpy array.
        """
        try:
            current_frame = self.get_current_frame()
            if current_frame is None:
                logging.warning("No current frame available")
                return None
                
            # Convert PIL Image to numpy array if needed
            if isinstance(current_frame, Image.Image):
                current_frame.save("current_frame.png")
                return np.array(current_frame)
                
            return current_frame
            
        except Exception as e:
            logging.error(f"Error getting screen image: {e}")
            return None

    def shutdown(self):
        """
        Shuts down the screen, terminating the Tkinter window and cleaning up resources.
        """
        try:
            logging.info("Shutting down screen...")
            self.shutdown_event.set()
            if not self.is_container and self.window:
                self.window.quit()
                self.window.destroy()
                logging.info("Tkinter window destroyed successfully.")
        except Exception as e:
            logging.error(f"Error during screen shutdown: {e}")

    def update_mouse_position_event(self, position):
        """
        Updates the current mouse position without an event.
        """
        self.mouse_position = position
        logging.debug(f"Mouse position updated to {self.mouse_position}")

    def get_resolution(self) -> Tuple[int, int]:
        """
        Retrieve the screen resolution.

        Returns:
            Tuple[int, int]: Width and height of the screen in pixels.
        """
        try:
            # Example using pyautogui
            import pyautogui
            return pyautogui.size()
        except Exception as e:
            logging.error(f"Error retrieving screen resolution: {e}")
            return (800, 600)  # Fallback resolution
