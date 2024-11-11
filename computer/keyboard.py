import logging
import threading

class Keyboard:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._is_running = False
        self._lock = threading.Lock()

    def initialize(self):
        """Initialize keyboard functionality."""
        try:
            with self._lock:
                self._is_running = True
            self.logger.info("Keyboard initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize keyboard: {e}")
            return False

    def stop(self):
        """Stop keyboard functionality."""
        try:
            with self._lock:
                self._is_running = False
            self.logger.info("Keyboard stopped")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping keyboard: {e}")
            return False
