import logging
import traceback
import time
from typing import Optional, Callable

class ErrorController:
    """
    A centralized controller to handle errors uniformly across the application.
    """

    def __init__(self, max_retries: int = 3, initial_retry_delay: int = 2, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.backoff_factor = backoff_factor

    def handle_error(self, error: Exception, context: str, retry_callback: Optional[Callable] = None) -> bool:
        """
        Handle an error by logging and optionally retrying the failed operation with exponential backoff.

        Args:
            error (Exception): The exception that was raised.
            context (str): A description of where the error occurred.
            retry_callback (Optional[Callable]): A callback function to retry the operation.

        Returns:
            bool: True if the operation was retried successfully, False otherwise.
        """
        logging.error(f"Error in {context}: {str(error)}")
        logging.debug(traceback.format_exc())

        if retry_callback:
            delay = self.initial_retry_delay
            for attempt in range(1, self.max_retries + 1):
                try:
                    logging.info(f"Retrying {context} in {delay} seconds... (Attempt {attempt}/{self.max_retries})")
                    time.sleep(delay)
                    retry_callback()
                    logging.info(f"Retry successful for {context} on attempt {attempt}.")
                    return True
                except Exception as retry_error:
                    logging.error(f"Retry {attempt} failed for {context}: {str(retry_error)}")
                    logging.debug(traceback.format_exc())
                    delay *= self.backoff_factor  # Exponential backoff
            logging.error(f"All {self.max_retries} retries failed for {context}.")
        return False

    def notify_failure(self, context: str, error: Exception):
        """
        Notify stakeholders about the failure.

        Args:
            context (str): A description of where the error occurred.
            error (Exception): The exception that was raised.
        """
        # Placeholder for notification logic (e.g., send email, alert system)
        logging.warning(f"Notification: Failure in {context}: {str(error)}")
