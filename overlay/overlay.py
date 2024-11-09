import cv2
import numpy as np
from PIL import Image
import logging

class Overlay:
    def __init__(self):
        pass

    def add_coordinate_system(self, image: np.ndarray, screen_width: int, screen_height: int) -> np.ndarray:
        """
        Adds a coordinate system overlay with numbered annotations to the image based on screen size.

        Args:
            image (np.ndarray): The original image.
            screen_width (int): Width of the screen in pixels.
            screen_height (int): Height of the screen in pixels.

        Returns:
            np.ndarray: The image with the coordinate system and numbers overlay.
        """
        try:
            # Ensure image dimensions match screen dimensions
            overlay_image = cv2.resize(image.copy(), (screen_width, screen_height))
            
            # Create semi-transparent overlay
            overlay = overlay_image.copy()
            
            # Determine grid size based on screen dimensions (e.g., 10x10 grid)
            num_columns = 10
            num_rows = 10
            grid_size_x = screen_width // num_columns
            grid_size_y = screen_height // num_rows

            # Draw vertical grid lines and add numbers at the top
            for idx, x in enumerate(range(0, screen_width, grid_size_x)):
                cv2.line(overlay, (x, 0), (x, screen_height), (255, 0, 0), 1)
                # Add coordinate numbers with increased size
                cv2.putText(
                    overlay,
                    str(x),
                    (x + 5, 50),  # Moved down for better visibility
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,  # Increased font size from 0.4 to 1.0
                    (0, 255, 255),  # Yellow color
                    2,  # Increased thickness from 1 to 2
                    cv2.LINE_AA
                )

            # Draw horizontal grid lines and add numbers on the left
            for idx, y in enumerate(range(0, screen_height, grid_size_y)):
                cv2.line(overlay, (0, y), (screen_width, y), (255, 0, 0), 1)
                cv2.putText(
                    overlay,
                    str(y),
                    (10, y + 35),  # Adjusted position for better visibility
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,  # Increased font size from 0.4 to 1.0
                    (0, 255, 255),  # Yellow color
                    2,  # Increased thickness from 1 to 2
                    cv2.LINE_AA
                )

            # Add final boundary lines
            cv2.line(overlay, (screen_width - 1, 0), (screen_width - 1, screen_height), (255, 0, 0), 1)
            cv2.line(overlay, (0, screen_height - 1), (screen_width, screen_height - 1), (255, 0, 0), 1)

            # Blend the overlay with the original image
            alpha = 0.7  # Transparency factor
            overlay_image = cv2.addWeighted(overlay_image, alpha, overlay, 1 - alpha, 0)

            return overlay_image
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
        Annotates the overlay image with the current mouse position.
        
        Args:
            overlay_image (np.ndarray): The image to annotate.
            mouse_position (tuple): The (x, y) position of the mouse.
        
        Returns:
            np.ndarray: The annotated image.
        """
        try:
            actual_position = (mouse_position[0], mouse_position[1])

            # Draw a more visible cursor indicator
            cv2.circle(overlay_image, actual_position, radius=5, color=(0, 255, 0), thickness=2)  # Outline
            cv2.circle(overlay_image, actual_position, radius=2, color=(0, 255, 0), thickness=-1)  # Filled center
            
            # Add position text with better visibility
            text = f"Mouse: ({mouse_position[0]}, {mouse_position[1]})"
            cv2.putText(
                overlay_image,
                text,
                (actual_position[0] + 10, actual_position[1] - 10),  # Adjusted position
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),  # Green color
                1,
                cv2.LINE_AA
            )
            
            return overlay_image
        except Exception as e:
            logging.error(f"Error annotating mouse position: {e}")
            return overlay_image

    def annotate_failed_attempt(self, overlay_image: np.ndarray, position: tuple) -> np.ndarray:
        """
        Annotates a failed attempt position with an X on the image.
        
        Args:
            overlay_image (np.ndarray): The image to annotate.
            position (tuple): The (x, y) position of the failed attempt.
        
        Returns:
            np.ndarray: The annotated image.
        """
        try:
            x, y = position
            size = 10  # Size of the X
            color = (0, 0, 255)  # Red color for X
            thickness = 2
            
            # Draw the X
            cv2.line(overlay_image, 
                     (x - size, y - size), 
                     (x + size, y + size), 
                     color, 
                     thickness)
            cv2.line(overlay_image, 
                     (x + size, y - size), 
                     (x - size, y + size), 
                     color, 
                     thickness)
            
            return overlay_image
        except Exception as e:
            logging.error(f"Error annotating failed attempt: {e}")
            return overlay_image
