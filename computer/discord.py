"""
This is the Discord environment, which is an application Bob can use.
"""
import logging
import time
import asyncio
import os
import docker
import subprocess
from computer.browser import Browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class Discord:
    def __init__(self, browser: Browser, username: str, password: str):
        self.browser = browser
        self.client = None
        self.root = None
        self.screen = None
        self.connected = False
        self.current_channel = None
        self.current_server = None
        self.target_server_id = None
        self.discord_url = "https://discord.com/channels/@me"
        self.username = username
        self.password = password

    def launch(self):
        """Launch Discord web application"""
        try:
            logging.info("Launching Discord...")
            
            # Navigate to Discord
            self.browser.navigate(self.discord_url)
            time.sleep(3)
                
            logging.info("Discord launched and logged in successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to launch Discord: {e}")
            return False

    def set_target_server(self, server_id):
        """
        Sets the target Discord server ID.
        """
        self.target_server_id = server_id

    def close(self):
        """Closes Discord and cleans up resources"""
        # ... existing code ...
        # Remove any attempts to destroy Tkinter root
        if self.root:
            try:
                self.root.destroy()
            except Exception as e:
                logging.error(f"Error destroying Discord root window: {e}")


