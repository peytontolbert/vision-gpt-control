"""
CommandFormatterAgent handles formatting of natural language responses into valid mouse commands
"""
import re
import logging
from agents.base import BaseAgent
from typing import Optional

class CommandFormatterAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def format_command(self, command: str) -> Optional[str]:
        """
        Format and validate the command to ensure it adheres to the expected format and bounds.
        
        Args:
            command (str): The raw command string.
        
        Returns:
            Optional[str]: The formatted command if valid, else None.
        """
        pattern = r"move to \(\s*(\d{1,4})\s*,\s*(\d{1,4})\s*\)(?:\s+and\s+(click|double-click|right-click))?"
        match = re.fullmatch(pattern, command.lower())
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            action = match.group(3) if match.group(3) else ""
            # Ensure coordinates are within custom bounds
            if 0 <= x <= 1000 and 0 <= y <= 600:
                formatted_command = f"move to ({x}, {y})"
                if action:
                    formatted_command += f" and {action}"
                return formatted_command
            else:
                self.logger.error(f"Command coordinates out of bounds: ({x}, {y})")
                return None
        else:
            self.logger.error(f"Command does not match expected format: {command}")
            return None
            
    def validate_command(self, command: str) -> bool:
        """
        Validates if a command string matches the expected format.
        
        Args:
            command (str): The command string to validate
            
        Returns:
            bool: True if command is valid, False otherwise
        """
        if not command:
            return False
            
        valid_pattern = r'^move to \(\d+,\s*\d+\)(?:\s+and\s+click)?$'
        return bool(re.match(valid_pattern, command)) 