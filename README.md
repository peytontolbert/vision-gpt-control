# Vision GPT Framework

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

The main entry point that orchestrates the automation workflow. Key features include:

- **Browser Control**: Uses `BrowserController` for browser automation and screenshot capture
- **Vision Integration**: Leverages `Qwen2VL` for visual element detection and verification
- **Task Management**: Implements `TaskManager` for organizing and executing automation tasks
- **Mouse Control**: Uses `MouseControllerHelper` for precise mouse movements and clicks

### Task Management (`agents/task_manager.py`)

Handles task orchestration and execution with features like:

- Task definition and sequencing
- Verification of task completion
- Retry mechanisms with configurable attempts
- Coordinate normalization and mouse position verification

### Example Usage: Discord Voice Channel Automation

```python
# Initialize controllers
browser = BrowserController(window_width=1000, window_height=1000)
qwen2vl = Qwen2VL()
task_manager = TaskManager(qwen2vl, browser)

# Define tasks
tasks = [
    Task(
        name="continue_in_browser",
        action="click",
        target="Continue in Browser",
        verification="Login textbox is visible"
    ),
    Task(
        name="enter_username",
        action="type",
        target="email or phone number field",
        value=DISCORD_USER,
        verification="Username entered"
    ),
    # Additional tasks...
]

# Add tasks to manager
for task in tasks:
    task_manager.add_task(task)

# Execute tasks
success = task_manager.run_tasks(max_retries=3, delay=2.0)
```

### Task Definition

Tasks are defined with the following attributes:

```python
Task(
    name="task_name",          # Unique identifier for the task
    action="action_type",      # click, type, or move
    target="element_name",     # Element to interact with
    value="optional_value",    # Text to type (for type action)
    verification="condition"   # Verification condition
)
```

### Environment Configuration

The system uses environment variables for sensitive information:

```bash
DISCORD_USER=your_username
DISCORD_PASS=your_password
```

Create a `.env` file in the project root with these variables.

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

### Basic Task Execution

```python
from agents.task_manager import TaskManager, Task
from computer.browser import BrowserController
from models.qwen2vl import Qwen2VL

# Initialize components
browser = BrowserController(window_width=1000, window_height=1000)
qwen2vl = Qwen2VL()
task_manager = TaskManager(qwen2vl, browser)

# Add tasks
task_manager.add_task(Task(
    name="click_button",
    action="click",
    target="Submit Button",
    verification="Check if button was clicked"
))

# Run tasks
success = task_manager.run_tasks(max_retries=3, delay=2.0)
```

### Mouse Control Helper

The `MouseControllerHelper` class provides precise mouse control:

```python
helper = MouseControllerHelper(browser, qwen2vl)

# Locate element coordinates
x, y = helper.locate_element_coordinates("Button Name")

# Verify mouse position
confidence = helper.verify_mouse_position(x, y, "Button Name")
```

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

