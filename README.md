# FlowController Automation Framework

## Overview

FlowController is a sophisticated automation framework designed to execute and manage complex tasks by orchestrating interactions between vision and natural language processing (NLP) agents. Leveraging advanced computer vision and NLP models, FlowController automates GUI-based workflows, enabling seamless interaction with applications through natural language commands and visual element detection.

## Features

- **Task Orchestration**: Manage and execute a queue of tasks with retry mechanisms and error handling.
- **NLP-Based Command Generation**: Interpret natural language inputs to generate precise mouse and keyboard commands.
- **Vision Integration**: Utilize computer vision agents to detect and interpret UI elements from screenshots.
- **Modular Architecture**: Easily extend and customize components such as agents and controllers to suit various automation needs.
- **Graceful Shutdown**: Handles shutdown signals to ensure all ongoing tasks are properly completed or halted.
- **Metrics and Logging**: Monitor task processing metrics and maintain detailed logs for debugging and performance analysis.

## Architecture

The system is composed of several key components:

### Main Module (`main.py`)

Serves as the entry point of the application. It initializes all necessary agents and controllers, sets up the environment, and starts the task processing loop.

### FlowController (`controllers/flow_controller.py`)

Handles the orchestration of tasks, manages the task queue, and oversees the interaction between vision and text agents to execute automated workflows.

### NLPMouseController (`controllers/nlp_mouse_controller.py`)

Processes NLP commands to control mouse movements and actions, enabling precise interaction with UI elements based on natural language inputs.

### VisionAgent (`agents/vision.py`)

Utilizes computer vision models to detect and interpret UI elements from screen images, providing necessary data for task execution.

### TextAgent (`agents/text.py`)

Generates actionable commands by interpreting text extracted from UI elements, facilitating seamless automation based on user-defined tasks.

### Computer Modules (`computer/`)

Interfaces with system components such as the screen, mouse, keyboard, and browser to capture screen images, execute mouse actions, type text, and manage browser interactions.

## Installation

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- Virtual Environment tool (optional but recommended)

### Steps

1. **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/FlowController.git
    cd FlowController
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
    - Download and place the required vision and NLP models as specified in the `models/` directory.
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

The `FlowController` automates the process of joining a Discord voice channel with the following steps:

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

Configuration files are located within their respective directories under `OmniParser/`. Adjust the settings in these files to fine-tune the behavior of vision and text agents. Important configurations include model paths, token IDs, and generation parameters.

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
- [BLIP-2 Models](https://huggingface.co/models?pipeline_tag=image-text-to-text)
- [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/)
- [OpenCV](https://opencv.org/)
