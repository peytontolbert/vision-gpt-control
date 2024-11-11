import cv2
import numpy as np
from PIL import Image
import logging

class Overlay:
    def __init__(self):
        # Define standard sizes
        self.VIEWPORT_WIDTH = 976
        self.VIEWPORT_HEIGHT = 732
        self.SCREENSHOT_WIDTH = 952
        self.SCREENSHOT_HEIGHT = 596

    def add_coordinate_system(self, image: np.ndarray, screen_width: int = None, screen_height: int = None) -> np.ndarray:
        """
        Adds a coordinate system overlay calibrated to browser viewport coordinates.

        Args:
            image (np.ndarray): The original image (screenshot).
            screen_width (int): Optional override for viewport width.
            screen_height (int): Optional override for viewport height.

        Returns:
            np.ndarray: The image with the coordinate system and numbers overlay.
        """
        try:
            # Use viewport dimensions for coordinate system
            viewport_width = screen_width or self.VIEWPORT_WIDTH
            viewport_height = screen_height or self.VIEWPORT_HEIGHT
            
            # Scale factor between screenshot and viewport
            scale_x = viewport_width / self.SCREENSHOT_WIDTH
            scale_y = viewport_height / self.SCREENSHOT_HEIGHT
            
            # Create overlay on screenshot size
            overlay_image = image.copy()
            overlay = overlay_image.copy()
            
            # Calculate grid intervals (show every 100 pixels of viewport)
            grid_interval_x = int(100 / scale_x)
            grid_interval_y = int(100 / scale_y)
            
            # Draw vertical lines and numbers
            for x in range(0, self.SCREENSHOT_WIDTH, grid_interval_x):
                # Calculate viewport coordinate
                viewport_x = int(x * scale_x)
                
                # Draw line
                cv2.line(overlay, (x, 0), (x, self.SCREENSHOT_HEIGHT), (0, 0, 0), 1)
                
                # Add coordinate label
                if viewport_x < viewport_width:  # Only show if within viewport
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = str(viewport_x)
                    font_scale = 0.5
                    thickness = 2
                    
                    # Background box
                    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                    cv2.rectangle(overlay,
                                (x + 2, 5),
                                (x + text_width + 8, 25),
                                (0, 0, 0),
                                -1)
                    
                    # Text
                    cv2.putText(overlay,
                              text,
                              (x + 5, 20),
                              font,
                              font_scale,
                              (255, 255, 255),
                              thickness,
                              cv2.LINE_AA)

            # Draw horizontal lines and numbers
            for y in range(0, self.SCREENSHOT_HEIGHT, grid_interval_y):
                # Calculate viewport coordinate
                viewport_y = int(y * scale_y)
                
                # Draw line
                cv2.line(overlay, (0, y), (self.SCREENSHOT_WIDTH, y), (0, 0, 0), 1)
                
                # Add coordinate label
                if viewport_y < viewport_height:  # Only show if within viewport
                    text = str(viewport_y)
                    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                    
                    # Background box
                    cv2.rectangle(overlay,
                                (5, y + 2),
                                (text_width + 15, y + 22),
                                (0, 0, 0),
                                -1)
                    
                    # Text
                    cv2.putText(overlay,
                              text,
                              (8, y + 17),
                              font,
                              font_scale,
                              (255, 255, 255),
                              thickness,
                              cv2.LINE_AA)

            # Blend overlay with original image
            alpha = 0.7
            result = cv2.addWeighted(overlay_image, alpha, overlay, 1 - alpha, 0)

            # Add scale information
            scale_text = f"Viewport: {viewport_width}x{viewport_height} | Screenshot: {self.SCREENSHOT_WIDTH}x{self.SCREENSHOT_HEIGHT}"
            cv2.putText(result,
                       scale_text,
                       (10, self.SCREENSHOT_HEIGHT - 10),
                       font,
                       0.5,
                       (0, 0, 0),
                       1,
                       cv2.LINE_AA)

            return result
        except Exception as e:
            logging.error(f"Error adding coordinate system overlay: {e}")
            return image

    def create_side_by_side_overlay(self, original_image: np.ndarray, overlay_image: np.ndarray) -> np.ndarray:
        """
        Creates a side-by-side comparison of the original and overlayed images.

        Args:
            original_image (np.ndarray): The original image.
            overlay_image (np.ndarray): The image with overlays.

        Returns:
            np.ndarray: Combined side-by-side image.
        """
        try:
            combined_image = np.hstack((original_image, overlay_image))
            return combined_image
        except Exception as e:
            logging.error(f"Error creating side-by-side overlay: {e}")
            return original_image

    def annotate_mouse_position(self, overlay_image: np.ndarray, mouse_position: tuple) -> np.ndarray:
        """
        Annotates the overlay image with the current mouse position, accounting for viewport scaling.
        
        Args:
            overlay_image (np.ndarray): The image to annotate.
            mouse_position (tuple): The (x, y) position in viewport coordinates.
        
        Returns:
            np.ndarray: The annotated image.
        """
        try:
            # Convert viewport coordinates to screenshot coordinates
            scale_x = self.SCREENSHOT_WIDTH / self.VIEWPORT_WIDTH
            scale_y = self.SCREENSHOT_HEIGHT / self.VIEWPORT_HEIGHT
            
            screen_x = int(mouse_position[0] * scale_x)
            screen_y = int(mouse_position[1] * scale_y)
            
            # Draw cursor indicator
            cv2.circle(overlay_image, (screen_x, screen_y), 5, (255, 0, 0), 2)  # Blue outline
            cv2.circle(overlay_image, (screen_x, screen_y), 2, (255, 0, 0), -1)  # Blue center
            
            # Add position text showing both coordinate systems
            text = f"Viewport: ({mouse_position[0]}, {mouse_position[1]}) | Screen: ({screen_x}, {screen_y})"
            cv2.putText(
                overlay_image,
                text,
                (screen_x + 10, screen_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                1,
                cv2.LINE_AA
            )
            
            return overlay_image
        except Exception as e:
            logging.error(f"Error annotating mouse position: {e}")
            return overlay_image

    def annotate_failed_attempt(self, overlay_image: np.ndarray, position: tuple) -> np.ndarray:
        """
        Annotates a failed attempt position with an X on the image, accounting for viewport scaling.
        
        Args:
            overlay_image (np.ndarray): The image to annotate.
            position (tuple): The (x, y) position of the failed attempt in viewport coordinates.
        
        Returns:
            np.ndarray: The annotated image.
        """
        try:
            # Convert viewport coordinates to screenshot coordinates
            scale_x = self.SCREENSHOT_WIDTH / self.VIEWPORT_WIDTH
            scale_y = self.SCREENSHOT_HEIGHT / self.VIEWPORT_HEIGHT
            
            screen_x = int(position[0] * scale_x)
            screen_y = int(position[1] * scale_y)
            
            size = 10  # Size of the X
            color = (0, 0, 255)  # Red color for X
            thickness = 2
            
            # Draw the X using screen coordinates
            cv2.line(overlay_image, 
                     (screen_x - size, screen_y - size), 
                     (screen_x + size, screen_y + size), 
                     color, 
                     thickness)
            cv2.line(overlay_image, 
                     (screen_x + size, screen_y - size), 
                     (screen_x - size, screen_y + size), 
                     color, 
                     thickness)
            
            # Add position text showing both coordinate systems
            text = f"Failed at - Viewport: ({position[0]}, {position[1]}) | Screen: ({screen_x}, {screen_y})"
            cv2.putText(
                overlay_image,
                text,
                (screen_x + 10, screen_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA
            )
            
            return overlay_image
        except Exception as e:
            logging.error(f"Error annotating failed attempt: {e}")
            return overlay_image
