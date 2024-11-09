from controllers.flow_controller import FlowController
from controllers.nlp_mouse_controller import NLPMouseController
from agents.text import TextAgent
from agents.vision import VisionAgent
from computer.computer import Computer
from computer.browser import Browser
from computer.mouse import Mouse
from agents.command_formatter import CommandFormatterAgent
import signal
import sys
import logging
import time

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG to capture all levels of logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("application.log"),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    # Initialize components
    text_agent = TextAgent()
    computer = Computer()
    computer.run()
    screen = computer.screen
    vision_agent = VisionAgent(screen=screen)
    browser = computer.apps["browser"]
    mouse = Mouse(target=browser, screen=screen, movement_speed=1.0)
    command_formatter = CommandFormatterAgent()
    flow_controller = FlowController(
        vision_agent=vision_agent,
        text_agent=text_agent,
        screen=screen,
        mouse=mouse,
        command_formatter=command_formatter
    )

    # Add tasks
    flow_controller.add_task("join_agora_discord_voice_channel")

    # Run tasks
    flow_controller.run_tasks()

    # Wait for the worker thread to finish
    flow_controller.wait_for_completion()

if __name__ == "__main__":
    main()

