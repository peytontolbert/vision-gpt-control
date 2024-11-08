from controllers.flow_controller import FlowController
from controllers.nlp_mouse_controller import NLPMouseController
from agents.text import TextAgent
from agents.vision import VisionAgent
from computer.computer import Computer
from computer.browser import Browser
from computer.mouse import Mouse
import signal
import sys
import logging
def main():
    # Initialize agents
    computer = Computer()
    computer.run()
    screen = computer.screen
    text_agent = TextAgent()
    vision_agent = VisionAgent(screen)
    
    # Initialize Browser
    browser = Browser(audio=computer.audio, microphone=computer.microphone, screen=screen)
    browser.launch()
    
    # Initialize Mouse with Browser as target and Screen as screen
    mouse = Mouse(target=browser, screen=screen)
    
    # Initialize FlowController with updated Mouse target
    flow_controller = FlowController(
        vision_agent=vision_agent,
        text_agent=text_agent,
        screen=screen,
        mouse=mouse  # Updated Mouse instance
    )
    
    # Example Task
    sample_task = "Join Agora Discord Voice Channel"
    flow_controller.add_task(sample_task)
    
    def shutdown_handler(signum, frame):
        logging.info("Received shutdown signal. Initiating graceful shutdown...")
        flow_controller.shutdown()
        flow_controller.wait_for_completion()
        logging.info("Shutdown complete.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    flow_controller.run_tasks()
    # Add tasks and other operations
    # ...

if __name__ == "__main__":
    main()

