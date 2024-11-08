-NLP Mouse Controller Environment
A module to interpret NLP commands that move the mouse. Commands could be in natural language format like “move to top right of button,” enabling the agent to control mouse movement based on spatial language.

-Prompt Generation from TextAgent

The TextAgent generates prompts for grounding dino or based on bounding boxes, masks, or text detected on the screen. This serves as input for further navigation or interaction commands, guiding the NLP mouse controller.
Detection Modules

Grounding DINO for Bounding Box Detection by text prompt

Detects UI elements, regions of interest, or other interactive components by marking them with bounding boxes. Grounding DINO is used for zero-shot localization based on descriptions.

-Omniparser for Text Parsing (YOLO + OCR)
Parses text within detected bounding boxes, combining YOLO’s detection capabilities with OCR to interpret labels, instructions, or other important text.

-Text Agent for NLP Mouse Command Generation
Analyzes bounding boxes, and text, translating this information into an actionable NLP command for the mouse. Commands generated are spatial and contextual (e.g., "move slightly left of button label").

-Accuracy Check and Iterative Refinement
The Vision LLM verifies the mouse position, determining if adjustments are needed. If the location is inaccurate, the LLM generates further commands until the mouse is correctly positioned.

-Repeat Until Task Completion
The Vision LLM and the NLP mouse controller continue iterating until the mouse reaches the final desired location or completes the intended interaction.


Flow Control Module
Purpose: Acts as the task manager, handling all interactions between components to progress through a defined task.
Functionality:
Manages the step-by-step flow using the Vision LLM's responses to sequence through actions.
Tracks task progress and dynamically adjusts actions based on feedback from each component.
For instance, to complete the task "Join Agora Discord Voice Channel," the flow module will:
Detect and identify necessary UI elements like the "Join Channel" button.
Direct bounding box, mask, and text detections to locate and interpret these elements.
Utilize Vision LLM to verify each step, prompting adjustments or re-steps as needed.
Output: Guides the task to completion by passing model results sequentially, handling each detected element until the "Join Channel" action is achieved.