# OmniParser

## Overview

OmniParser is an advanced GUI automation tool that leverages state-of-the-art vision and natural language processing (NLP) models to interpret and interact with graphical user interfaces. Designed to automate tasks such as navigating web applications, controlling the mouse, and executing complex workflows, OmniParser serves as a robust solution for enhancing productivity and streamlining interactions with software interfaces.

## Features

- **NLP-Based Mouse Control**: Interpret natural language commands to perform precise mouse movements and actions within applications.
- **Vision Integration**: Utilize vision agents like Grounding DINO and Omniparser to detect and interpret UI elements from screenshots.
- **Task Management**: Queue and process tasks efficiently with retry mechanisms and error handling.
- **Modular Architecture**: Easily extend and customize components like agents and controllers to fit various automation needs.
- **Metrics and Logging**: Monitor task processing metrics and maintain detailed logs for debugging and performance analysis.

## Architecture

The system is composed of several key components:

### FlowController

Handles the orchestration of tasks, manages the task queue, and oversees the interaction between vision and text agents to execute automated workflows.

### NLPMouseController

Processes NLP commands to control mouse movements and actions, enabling precise interaction with UI elements based on natural language inputs.

### VisionAgent

Utilizes models like Grounding DINO and Omniparser to detect and interpret UI elements from screen images, providing necessary data for task execution.

### TextAgent

Generates actionable commands by interpreting text extracted from UI elements, facilitating seamless automation based on user-defined tasks.

### Computer Modules

Interfaces with system components such as the screen, mouse, and browser to capture screen images, execute mouse actions, and manage browser interactions.

## Installation

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- Virtual Environment tool (optional but recommended)

### Steps

1. **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/OmniParser.git
    cd OmniParser
    ```

2. **Create and Activate Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure Models**
    - Download and place the required vision and NLP models as specified in the `OmniParser` directory.
    - Ensure that configuration files (`config.json`, `generation_config.json`, etc.) are correctly set up.

## Usage

### Running the Application

Execute the main script to start processing tasks:
```bash
python main.py
```

### Adding Tasks

Tasks can be added programmatically within `main.py` or through an interface if implemented:
```python
sample_task = "Join Agora Discord Voice Channel"
flow_controller.add_task(sample_task)
```

### Graceful Shutdown

The application listens for shutdown signals (`SIGINT`, `SIGTERM`) to terminate gracefully, ensuring all ongoing tasks are completed or properly halted.

## Example Task: Join Agora Discord Voice Channel

The FlowController automates the process of joining a Discord voice channel with the following steps:

1. **Navigate to Discord Website**: Opens the Discord URL in the browser.
2. **Login (If Necessary)**: Enters credentials to authenticate the user.
3. **Navigate to Voice Channel**: Locates the specific voice channel within Discord.
4. **Join Voice Channel**: Executes the mouse click to join the channel.
5. **Verification**: Confirms successful joining by checking UI elements.

### Code Snippet
```python:controllers/flow_controller.py
def _join_agora_discord_voice_channel(self) -> bool:
    """
    Steps to join the Agora Discord Voice Channel with enhanced vision capabilities.
    """
    try:
        logging.info("Starting task: Join Agora Discord Voice Channel")
        
        # Step 0: Click "Continue in Browser" link
        self._click_element("Continue in Browser")
        
        # Step 1: Navigate to Discord URL
        self._click_element("Navigate to Discord Website")
        
        # Step 2: Login if necessary
        if self.vision_agent.verify_element("login_page", timeout=10):
            self._input_text("Enter Discord Username", "YourUsername")
            self._input_text("Enter Discord Password", "YourPassword")
        
        # Step 3: Navigate to Voice Channel
        self._click_element("Navigate to Agora Voice Channel")
        
        # Step 4: Join Voice Channel
        self._click_element("Join Agora Voice Channel")
        
        # Step 5: Verify Successful Joining
        if not self.vision_agent.verify_element("joined_agora_voice", timeout=10):
            raise TaskProcessingError("Failed to join Agora Discord Voice Channel.")
        
        logging.info("Task 'Join Agora Discord Voice Channel' completed successfully.")
        return True
    except TaskProcessingError as e:
        self.metrics['tasks_failed'] += 1
        logging.error(f"Task failed: {e}", exc_info=True)
        return False
    except Exception as e:
        self.metrics['tasks_failed'] += 1
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return False
```

## Configuration

Configuration files are located within their respective model directories under `OmniParser/`. Adjust the settings in these files to fine-tune the behavior of vision and text agents. Important configurations include model paths, token IDs, and generation parameters.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. **Fork the Repository**
2. **Create a Feature Branch**
    ```bash
    git checkout -b feature/YourFeature
    ```
3. **Commit Your Changes**
    ```bash
    git commit -m "Add your feature"
    ```
4. **Push to the Branch**
    ```bash
    git push origin feature/YourFeature
    ```
5. **Open a Pull Request**

Please ensure that your code adheres to the project's coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License and the GNU Affero General Public License v3.0. See the respective `LICENSE` files in the project directories for more details.

## Acknowledgements

- [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO)
- [OmniParser Project Page](https://microsoft.github.io/OmniParser/)
- [BLIP-2 Models](https://huggingface.co/models?pipeline_tag=image-text-to-text)
- [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/)
- [OpenCV](https://opencv.org/)
